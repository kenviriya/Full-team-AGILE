#!/usr/bin/env python3
"""OpenAI-compatible gateway protocol for host-mediated agent delegation.

The gateway proposes normalized repository tool calls. It never executes them.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

MAX_TURNS = 25
MAX_SECONDS = 10 * 60
TOOLS = {
    "read": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"], "additionalProperties": False},
    "glob": {"type": "object", "properties": {"pattern": {"type": "string"}, "path": {"type": "string"}}, "required": ["pattern"], "additionalProperties": False},
    "grep": {"type": "object", "properties": {"pattern": {"type": "string"}, "path": {"type": "string"}}, "required": ["pattern"], "additionalProperties": False},
    "bash": {"type": "object", "properties": {"command": {"type": "string"}, "description": {"type": "string"}}, "required": ["command"], "additionalProperties": False},
    "write": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"], "additionalProperties": False},
    "edit": {"type": "object", "properties": {"path": {"type": "string"}, "old_string": {"type": "string"}, "new_string": {"type": "string"}}, "required": ["path", "old_string", "new_string"], "additionalProperties": False},
}
SYSTEM_PROMPT = (
    "You are a delegated software-engineering agent. Use only the supplied tools. "
    "All tool actions are executed by a host which may deny them. Work only in the supplied workspace. "
    "Do not request credentials, environment variables, or files outside the workspace. "
    "When finished, respond with a concise final report."
)


def error(code, message, state=None):
    result = {"version": 1, "type": "error", "code": code, "message": message}
    if state is not None:
        result["state"] = state
    return result


def clean_text(value):
    return value if isinstance(value, str) else ""


def sanitize(value, api_key=None):
    if not isinstance(value, str):
        return value
    if api_key:
        return value.replace(api_key, "[redacted]")
    return value


def endpoint(base_url):
    if not isinstance(base_url, str) or not base_url.strip():
        raise ValueError("OPENAI_BASE_URL is not set")
    parsed = urllib.parse.urlparse(base_url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("OPENAI_BASE_URL must be an absolute http(s) URL without credentials, query, or fragment")
    path = parsed.path.rstrip("/")
    if not path.endswith("/v1"):
        path = f"{path}/v1"
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, f"{path}/chat/completions", "", "", ""))


def tool_definitions():
    return [{"type": "function", "function": {"name": name, "parameters": schema}} for name, schema in TOOLS.items()]


def valid_state(state):
    return isinstance(state, dict) and state.get("version") == 1 and isinstance(state.get("messages"), list)


def validate_limits(state, now):
    if state["turns"] >= MAX_TURNS:
        return "turn_limit_reached"
    if now - state["startedMonotonic"] >= MAX_SECONDS:
        return "time_limit_reached"
    return None


def normalize_tool_calls(message):
    calls = message.get("tool_calls", [])
    if not isinstance(calls, list):
        raise ValueError("tool calls must be a list")
    if len(calls) > 1:
        raise ValueError("only one tool call per response is supported")
    requests = []
    for call in calls:
        if not isinstance(call, dict) or call.get("type") != "function":
            raise ValueError("tool call is malformed")
        call_id = call.get("id")
        function = call.get("function")
        if not isinstance(call_id, str) or not isinstance(function, dict):
            raise ValueError("tool call is malformed")
        name = function.get("name")
        if name not in TOOLS:
            raise ValueError(f"unknown tool {name!r}")
        try:
            arguments = json.loads(function.get("arguments", ""))
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("tool call arguments are not valid JSON") from exc
        if not isinstance(arguments, dict):
            raise ValueError("tool call arguments must be an object")
        required = TOOLS[name].get("required", [])
        if any(not isinstance(arguments.get(key), str) for key in required):
            raise ValueError("tool call has missing or invalid arguments")
        if set(arguments) - set(TOOLS[name]["properties"]):
            raise ValueError("tool call contains unsupported arguments")
        requests.append({"callId": call_id, "tool": name, "input": arguments})
    return requests


def request_completion(state, transport, now):
    limited = validate_limits(state, now)
    if limited:
        return error(limited, "Gateway delegation limit reached.", state)
    payload = {"model": state["model"], "messages": state["messages"], "tools": tool_definitions(), "stream": False}
    try:
        response = transport(state["endpoint"], state["apiKey"], payload)
    except GatewayFailure as exc:
        return error(exc.code, exc.message, public_state(state))
    state["turns"] += 1
    try:
        message = response["choices"][0]["message"]
        if not isinstance(message, dict):
            raise ValueError("completion message is malformed")
        state["messages"].append(message)
        requests = normalize_tool_calls(message)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        return error("gateway_response_invalid", sanitize(str(exc), state["apiKey"]), public_state(state))
    if requests:
        return {"version": 1, "type": "tool_request", "turn": state["turns"], "toolRequests": requests, "state": public_state(state)}
    return {"version": 1, "type": "final", "turn": state["turns"], "text": clean_text(message.get("content")), "state": public_state(state)}


class GatewayFailure(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message


def http_transport(url, api_key, payload):
    data = json.dumps(payload).encode()
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raise GatewayFailure("gateway_request_failed", f"Gateway request failed: HTTP {exc.code}.") from exc
    except (urllib.error.URLError, TimeoutError, OSError):
        raise GatewayFailure("gateway_request_failed", "Gateway request failed.")
    except json.JSONDecodeError as exc:
        raise GatewayFailure("gateway_response_invalid", "Gateway response was not valid JSON.") from exc


def public_state(state):
    return {
        "version": 1,
        "model": state["model"],
        "turns": state["turns"],
        "startedMonotonic": state["startedMonotonic"],
        "workspace": state["workspace"],
        "messages": state["messages"],
    }


def private_state(public, api_key, url):
    state = dict(public)
    state["apiKey"] = api_key
    state["endpoint"] = url
    return state


def start(frame, environ, now, transport=http_transport):
    model = frame.get("model")
    task = frame.get("task")
    workspace = frame.get("workspace")
    if not isinstance(model, str) or not model.strip() or not isinstance(task, str) or not isinstance(workspace, dict):
        return error("gateway_request_invalid", "Gateway start request is invalid.")
    api_key = environ.get("OPENAI_API_KEY")
    if not api_key:
        return error("gateway_configuration_invalid", "OPENAI_API_KEY is not set.")
    try:
        url = endpoint(environ.get("OPENAI_BASE_URL"))
    except ValueError as exc:
        return error("gateway_configuration_invalid", str(exc))
    state = {
        "version": 1,
        "model": model,
        "turns": 0,
        "startedMonotonic": now,
        "workspace": workspace,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": task}],
        "apiKey": api_key,
        "endpoint": url,
    }
    return request_completion(state, transport, now)


def resume(frame, environ, now, transport=http_transport):
    public = frame.get("state")
    result = frame.get("result")
    if not valid_state(public) or not isinstance(result, dict):
        return error("gateway_request_invalid", "Gateway tool result request is invalid.")
    api_key = environ.get("OPENAI_API_KEY")
    if not api_key:
        return error("gateway_configuration_invalid", "OPENAI_API_KEY is not set.")
    try:
        url = endpoint(environ.get("OPENAI_BASE_URL"))
    except ValueError as exc:
        return error("gateway_configuration_invalid", str(exc))
    call_id = result.get("callId")
    content = result.get("content")
    if not isinstance(call_id, str) or not isinstance(content, str) or not isinstance(result.get("isError"), bool):
        return error("gateway_request_invalid", "Gateway tool result is invalid.")
    state = private_state(public, api_key, url)
    limited = validate_limits(state, now)
    if limited:
        return error(limited, "Gateway delegation limit reached.", public_state(state))
    state["messages"].append({"role": "tool", "tool_call_id": call_id, "content": sanitize(content, api_key)})
    return request_completion(state, transport, now)


def handle(frame, environ=None, now=None, transport=http_transport):
    environ = os.environ if environ is None else environ
    now = time.monotonic() if now is None else now
    if not isinstance(frame, dict):
        return error("gateway_request_invalid", "Gateway request must be an object.")
    if frame.get("op") == "start":
        return start(frame, environ, now, transport)
    if frame.get("op") == "tool_result":
        return resume(frame, environ, now, transport)
    return error("gateway_request_invalid", "Gateway operation is unknown.")


def main():
    try:
        frame = json.load(sys.stdin)
        print(json.dumps(handle(frame), separators=(",", ":")))
    except json.JSONDecodeError:
        print(json.dumps(error("gateway_request_invalid", "Gateway request was not valid JSON.")))


if __name__ == "__main__":
    main()
