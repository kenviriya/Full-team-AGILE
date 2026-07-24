#!/usr/bin/env python3

import contextlib
import importlib.util
import io
import json
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_SPEC = importlib.util.spec_from_file_location("show_agent_models", ROOT / "scripts/show-agent-models.py")
MODELS = importlib.util.module_from_spec(MODEL_SPEC)
MODEL_SPEC.loader.exec_module(MODELS)
GATEWAY_SPEC = importlib.util.spec_from_file_location("gateway_agent", ROOT / "scripts/gateway-agent.py")
GATEWAY = importlib.util.module_from_spec(GATEWAY_SPEC)
GATEWAY_SPEC.loader.exec_module(GATEWAY)

assert MODELS.mapping("invocation", '{"product-manager":"provider/model:v1"}') == {
    "product-manager": "provider/model:v1"
}

warnings = io.StringIO()
with contextlib.redirect_stderr(warnings):
    parsed = MODELS.mapping(
        "repository",
        {"qa-engineer": "provider/qa", "unknown": "x", "code-reviewer": ""},
    )
assert parsed == {"qa-engineer": "provider/qa"}
assert "agent=unknown" in warnings.getvalue()
assert "agent=code-reviewer" in warnings.getvalue()
assert MODELS.route("opus") == "native"
assert MODELS.route("provider/custom-model") == "gateway"

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    data = root / "data"
    (root / ".claude").mkdir()
    (root / ".claude/full-team-agile.json").write_text(
        json.dumps({"agentModels": {"backend-engineer": "haiku"}})
    )
    prompt = (
        "Implement the feature.\n"
        '<!-- full-team-agile-agent-models: {"invocation":{"backend-engineer":"invoke/model"},'
        '"feature":{"backend-engineer":"feature/model"}} -->'
    )
    event = {
        "cwd": str(root),
        "tool_name": "Agent",
        "tool_input": {
            "subagent_type": "full-team-agile:backend-engineer",
            "prompt": prompt,
        },
    }
    denied = MODELS.pre_tool_use(event, ROOT, '{"backend-engineer":"user/model"}')
    assert denied["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "gateway" in denied["hookSpecificOutput"]["permissionDecisionReason"]

    native = MODELS.pre_tool_use(
        {**event, "tool_input": {**event["tool_input"], "prompt": "Implement the feature."}},
        ROOT,
        '{"backend-engineer":"haiku"}',
    )
    output = native["hookSpecificOutput"]
    assert output["updatedInput"]["model"] == "haiku"
    assert "permissionDecision" not in output

with tempfile.TemporaryDirectory() as directory:
    workspace = Path(directory)
    api = workspace / "api"
    web = workspace / "web"
    for repo, document in (
        (api, {"agentModels": {"backend-engineer": "haiku"}}),
        (web, {"agentModels": {"backend-engineer": "sonnet"}}),
    ):
        (repo / ".claude").mkdir(parents=True)
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        (repo / ".claude/full-team-agile.json").write_text(json.dumps(document))
    event = {
        "tool_name": "Agent",
        "tool_input": {
            "subagent_type": "full-team-agile:backend-engineer",
            "prompt": "Implement the feature.",
        },
    }
    api_output = MODELS.pre_tool_use({**event, "cwd": str(api)}, ROOT, "{}")
    web_output = MODELS.pre_tool_use({**event, "cwd": str(web)}, ROOT, "{}")
    assert api_output["hookSpecificOutput"]["updatedInput"]["model"] == "haiku"
    assert web_output["hookSpecificOutput"]["updatedInput"]["model"] == "sonnet"

    empty_config = api / ".claude/full-team-agile.json"
    empty_config.write_text('{"agentModels": {}}')
    fallback = MODELS.pre_tool_use({**event, "cwd": str(api)}, ROOT, '{"backend-engineer":"fable"}')
    assert fallback["hookSpecificOutput"]["updatedInput"]["model"] == "fable"
    assert json.loads(empty_config.read_text())["agentModels"] == {}

output = io.StringIO()
with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(output):
    root = Path(directory)
    (root / ".claude").mkdir()
    (root / ".claude/full-team-agile.json").write_text(
        json.dumps({"agentModels": {"product-manager": "repo/model"}})
    )
    MODELS.startup(ROOT, '{"product-manager":"user/model","ux-designer":"haiku"}', root)

lines = output.getvalue().splitlines()
assert len(lines) == len(MODELS.AGENTS)
assert "product-manager -> repo/model (repository, gateway)" in lines[0]
assert "ux-designer -> haiku (user/global, native)" in lines[1]

hooks = json.loads((ROOT / "hooks/hooks.json").read_text())["hooks"]
assert hooks["PreToolUse"][0]["matcher"] == "Agent"
assert len(hooks["SessionStart"]) == 1
for event in ("SessionStart", "PreToolUse"):
    command = hooks[event][0]["hooks"][0]["command"]
    assert "${user_config." not in command
    assert "CLAUDE_PLUGIN_OPTION_AGENT_MODELS=" not in command

sent = []

def transport(url, api_key, payload):
    sent.append((url, api_key, payload))
    if len(sent) == 1:
        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": "call-1",
                                "type": "function",
                                "function": {"name": "read", "arguments": '{"path":"README.md"}'},
                            }
                        ],
                    }
                }
            ]
        }
    return {"choices": [{"message": {"role": "assistant", "content": "Done."}}]}

frame = {
    "op": "start",
    "model": "provider/custom-model",
    "task": "Read the README.",
    "workspace": {"root": "/repo", "worktree": "/repo", "branch": "feature/x", "baseCommit": "abc"},
}
environ = {"OPENAI_BASE_URL": "https://gateway.example", "OPENAI_API_KEY": "secret-value"}
first = GATEWAY.handle(frame, environ, 100, transport)
assert first["type"] == "tool_request"
assert first["toolRequests"] == [{"callId": "call-1", "tool": "read", "input": {"path": "README.md"}}]
assert sent[0][0] == "https://gateway.example/v1/chat/completions"
assert sent[0][2]["model"] == "provider/custom-model"
assert "secret-value" not in json.dumps(first)
second = GATEWAY.handle(
    {"op": "tool_result", "state": first["state"], "result": {"callId": "call-1", "isError": False, "content": "README"}},
    environ,
    101,
    transport,
)
assert second["type"] == "final"
assert second["text"] == "Done."

missing = GATEWAY.handle(frame, {"OPENAI_BASE_URL": "https://gateway.example"}, 100, transport)
assert missing["code"] == "gateway_configuration_invalid"
assert "secret-value" not in json.dumps(missing)
invalid_url = GATEWAY.handle(frame, {"OPENAI_BASE_URL": "ftp://gateway.example", "OPENAI_API_KEY": "secret-value"}, 100, transport)
assert invalid_url["code"] == "gateway_configuration_invalid"

bad_tool = GATEWAY.handle(
    frame,
    environ,
    100,
    lambda *_: {"choices": [{"message": {"role": "assistant", "tool_calls": [{"id": "x", "type": "function", "function": {"name": "unknown", "arguments": "{}"}}]}}]},
)
assert bad_tool["code"] == "gateway_response_invalid"

limit_state = {"version": 1, "model": "provider/model", "turns": 25, "startedMonotonic": 0, "workspace": {}, "messages": []}
limited = GATEWAY.handle(
    {"op": "tool_result", "state": limit_state, "result": {"callId": "x", "isError": True, "content": "denied"}},
    environ,
    1,
    transport,
)
assert limited["code"] == "turn_limit_reached"
timeout_state = {"version": 1, "model": "provider/model", "turns": 0, "startedMonotonic": 0, "workspace": {}, "messages": []}
timed_out = GATEWAY.handle(
    {"op": "tool_result", "state": timeout_state, "result": {"callId": "x", "isError": True, "content": "denied"}},
    environ,
    GATEWAY.MAX_SECONDS,
    transport,
)
assert timed_out["code"] == "time_limit_reached"

print("agent model and gateway protocol checks passed")
