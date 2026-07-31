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


def artifact_root(value):
    if value in (None, ""):
        return ""
    if not isinstance(value, str):
        print(f"full-team-agile: warning: artifact root rejected={value!r}", file=sys.stderr)
        return ""
    if (
        value.startswith(("/", "~"))
        or "\\" in value
        or re.match(r"^[A-Za-z]:", value)
        or any(not part or part in {".", ".."} for part in value.split("/"))
        or any(ord(character) < 32 for character in value)
    ):
        print(f"full-team-agile: warning: artifact root rejected={value!r}", file=sys.stderr)
        return ""
    return value


DURABLE_ARTIFACTS = {
    "Features": frozenset(
        ("State.md", "01-prd.md", "02-ui-spec.md", "03-review-notes.md", "04-test-report.md")
    ),
    "Sprints": frozenset(
        ("State.md", "01-sprint-plan.md", "02-integration-report.md", "03-sprint-recap.md")
    ),
    "Releases": frozenset(
        ("State.md", "01-release-plan.md", "02-release-validation.md", "03-release-recap.md")
    ),
}


def durable_artifact_path(path, cwd, artifact_value):
    if not isinstance(path, str) or not path:
        return False
    base = Path(cwd if isinstance(cwd, str) else Path.cwd()).resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = base / candidate
    try:
        parts = list(Path(os.path.normpath(candidate)).relative_to(base).parts)
    except ValueError:
        return False
    candidates = [parts]
    root = artifact_root(artifact_value)
    prefix = root.split("/") if root else []
    if prefix and parts[:len(prefix)] == prefix:
        candidates.insert(0, parts[len(prefix):])
    for candidate in candidates:
        if len(candidate) == 4 and candidate[0] in DURABLE_ARTIFACTS:
            return candidate[3] in DURABLE_ARTIFACTS[candidate[0]]
    return False


def artifact_write_denial(path):
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                f"Durable artifact path {path!r} must be stored in the Obsidian MCP vault. "
                "Use mcp__obsidian__write_note or mcp__obsidian__patch_note instead of Write/Edit."
            ),
        }
    }


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


def delegation_repository(metadata):
    value = metadata.get("repository")
    if not isinstance(value, str) or not value.strip():
        if value not in (None, ""):
            warn("delegation repository", None, value)
        return None
    path = Path(value)
    if not path.is_absolute():
        warn("delegation repository", None, value)
        return None
    try:
        canonical = path.resolve(strict=True)
    except OSError as error:
        warn("delegation repository", None, str(error))
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(canonical), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        warn("delegation repository", None, str(error))
        return None
    root = Path(result.stdout.strip()).resolve()
    if root != canonical:
        warn("delegation repository", None, value)
        return None
    return root


def candidates(agent, metadata, root, plugin_root, user_value):
    repository = repository_mapping(root) if root is not None else {}
    scopes = (
        ("invocation", mapping("invocation", metadata.get("invocation"))),
        ("feature", mapping("feature", metadata.get("feature"))),
        ("repository", repository),
        ("user/global", mapping("user/global", user_value)),
        ("bundled", bundled_defaults(plugin_root)),
    )
    return [(scope, values[agent]) for scope, values in scopes if agent in values]


def selected_model(agent, metadata, root, plugin_root, user_value):
    values = candidates(agent, metadata, root, plugin_root, user_value)
    return values[0] if values else (None, None)


def route(model):
    return "native" if model in NATIVE_MODELS else "gateway"


def pre_tool_use(event, plugin_root, user_value, artifact_value=""):
    tool_input = event.get("tool_input")
    tool_name = event.get("tool_name")
    if tool_name in {"Write", "Edit"} and isinstance(tool_input, dict):
        path = tool_input.get("file_path")
        if durable_artifact_path(path, event.get("cwd", Path.cwd()), artifact_value):
            return artifact_write_denial(path)
        return None
    if tool_name != "Agent" or not isinstance(tool_input, dict):
        return None
    agent = agent_name(tool_input.get("subagent_type"))
    if not agent:
        return None
    metadata, clean_prompt = prompt_metadata(tool_input.get("prompt", ""))
    scope, model = selected_model(
        agent,
        metadata,
        delegation_repository(metadata),
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


def startup(plugin_root, user_value, cwd, artifact_value=""):
    print(f"full-team-agile: artifact root -> {artifact_root(artifact_value) or '<vault root>'} (vault-relative)")
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
    artifact_value = os.environ.get("CLAUDE_PLUGIN_OPTION_ARTIFACT_ROOT", "")
    if len(sys.argv) == 1 or sys.argv[1] == "startup":
        startup(plugin_root, user_value, Path.cwd(), artifact_value)
        return
    event = json.load(sys.stdin)
    if sys.argv[1] != "pre-agent":
        raise SystemExit(f"unknown mode: {sys.argv[1]}")
    output = pre_tool_use(event, plugin_root, user_value, artifact_value)
    if output:
        print(json.dumps(output))


if __name__ == "__main__":
    main()
