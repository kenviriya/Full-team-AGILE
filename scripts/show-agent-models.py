#!/usr/bin/env python3
"""Resolve bundled-agent models for startup and native Agent hooks."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

AGENTS = (
    "product-manager",
    "ux-designer",
    "backend-engineer",
    "frontend-engineer",
    "qa-engineer",
    "code-reviewer",
)
NATIVE_MODELS = frozenset(("sonnet", "opus", "haiku", "fable"))
METADATA_RE = re.compile(
    r"\n?<!-- full-team-agile-agent-models: (?P<value>\{.*?\}) -->\n?",
    re.DOTALL,
)


def warn(scope, agent, value):
    print(
        f"full-team-agile: warning: {scope} model mapping"
        f" agent={agent or '<mapping>'} rejected={value!r}",
        file=sys.stderr,
    )


def mapping(scope, value):
    if value in (None, ""):
        return {}
    try:
        value = json.loads(value) if isinstance(value, str) else value
    except (json.JSONDecodeError, TypeError):
        warn(scope, None, value)
        return {}
    if not isinstance(value, dict):
        warn(scope, None, value)
        return {}
    result = {}
    for agent, model in value.items():
        if agent not in AGENTS or not isinstance(model, str) or not model.strip():
            warn(scope, agent, model)
        else:
            result[agent] = model
    return result


def repository_root(cwd):
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        )
        return Path(result.stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        return Path(cwd)


def repository_mapping(root):
    path = root / ".claude" / "full-team-agile.json"
    if not path.exists():
        return {}
    try:
        document = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        warn("repository", None, str(error))
        return {}
    if not isinstance(document, dict):
        warn("repository", None, document)
        return {}
    return mapping("repository", document.get("agentModels"))


def bundled_defaults(plugin_root):
    defaults = {}
    for agent in AGENTS:
        try:
            for line in (plugin_root / "agents" / f"{agent}.md").read_text().splitlines():
                if line.startswith("model:"):
                    defaults[agent] = line.split(":", 1)[1].strip()
                    break
        except OSError as error:
            warn("bundled", agent, str(error))
    return defaults


def agent_name(value):
    name = value.rsplit(":", 1)[-1] if isinstance(value, str) else ""
    return name if name in AGENTS else None


def prompt_metadata(prompt):
    match = METADATA_RE.search(prompt or "")
    if not match:
        return {}, (prompt or "")
    try:
        document = json.loads(match.group("value"))
    except json.JSONDecodeError:
        warn("delegation", None, match.group("value"))
        document = {}
    if not isinstance(document, dict):
        warn("delegation", None, document)
        document = {}
    return document, METADATA_RE.sub("\n", prompt or "").strip()


def candidates(agent, metadata, root, plugin_root, user_value):
    scopes = (
        ("invocation", mapping("invocation", metadata.get("invocation"))),
        ("feature", mapping("feature", metadata.get("feature"))),
        ("repository", repository_mapping(root)),
        ("user/global", mapping("user/global", user_value)),
        ("bundled", bundled_defaults(plugin_root)),
    )
    return [(scope, values[agent]) for scope, values in scopes if agent in values]


def selected_model(agent, metadata, root, plugin_root, user_value):
    values = candidates(agent, metadata, root, plugin_root, user_value)
    return values[0] if values else (None, None)


def route(model):
    return "native" if model in NATIVE_MODELS else "gateway"


def pre_tool_use(event, plugin_root, user_value):
    tool_input = event.get("tool_input")
    if event.get("tool_name") != "Agent" or not isinstance(tool_input, dict):
        return None
    agent = agent_name(tool_input.get("subagent_type"))
    if not agent:
        return None
    metadata, clean_prompt = prompt_metadata(tool_input.get("prompt", ""))
    scope, model = selected_model(
        agent,
        metadata,
        repository_root(event.get("cwd", ".")),
        plugin_root,
        user_value,
    )
    if not model:
        warn("bundled", agent, "missing default")
        return None
    if route(model) == "gateway":
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"full-team-agile selected gateway model {model!r} for {agent} ({scope}). "
                    "Use the feature workflow gateway bridge; non-native models cannot run through Agent."
                ),
            }
        }
    updated = dict(tool_input)
    updated["prompt"] = clean_prompt
    updated["model"] = model
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "updatedInput": updated,
            "additionalContext": f"full-team-agile selected {model} for {agent} ({scope}, native).",
        }
    }


def startup(plugin_root, user_value, cwd):
    repository = repository_mapping(repository_root(cwd))
    user = mapping("user/global", user_value)
    defaults = bundled_defaults(plugin_root)
    for agent in AGENTS:
        if agent in repository:
            scope, model = "repository", repository[agent]
        elif agent in user:
            scope, model = "user/global", user[agent]
        else:
            scope, model = "bundled", defaults.get(agent, "<missing>")
        print(f"full-team-agile: {agent} -> {model} ({scope}, {route(model)})")


def main():
    plugin_root = Path(os.environ["CLAUDE_PLUGIN_ROOT"])
    user_value = os.environ.get("CLAUDE_PLUGIN_OPTION_AGENT_MODELS", "{}")
    if len(sys.argv) == 1 or sys.argv[1] == "startup":
        startup(plugin_root, user_value, Path.cwd())
        return
    event = json.load(sys.stdin)
    if sys.argv[1] != "pre-agent":
        raise SystemExit(f"unknown mode: {sys.argv[1]}")
    output = pre_tool_use(event, plugin_root, user_value)
    if output:
        print(json.dumps(output))


if __name__ == "__main__":
    main()
