# Full-team-AGILE

A Claude Code plugin for delivering a feature through product definition, conditional UX, targeted implementation, QA, and independent review. Feature state and artifacts are stored in the Obsidian Vault so work can resume across sessions.

It ships one `feature` skill and six focused agents:

| Item | Use it for |
| --- | --- |
| `feature` skill | Orchestrating a feature from questions through QA and review, with durable state. |
| `product-manager` | Clarifying requirements and writing a concise PRD with testable acceptance criteria. |
| `ux-designer` | Producing a UI specification when an approved feature has a user-facing surface. |
| `backend-engineer` | Implementing server-side, API, database, and integration work. |
| `frontend-engineer` | Implementing client-side, component, state, and accessibility work. |
| `qa-engineer` | Validating acceptance criteria with pass/fail evidence. |
| `code-reviewer` | Independently reviewing the completed work without editing it. |

## Install

In Claude Code, add this repository as a marketplace, then install the plugin:

```text
/plugin marketplace add kenviriya/Full-team-AGILE
```

```text
/plugin install full-team-agile@full-team-agile
```

### Codex

```bash
codex plugin marketplace add kenviriya/Full-team-AGILE
codex plugin install full-team-agile@full-team-agile
```

### Kimi Code

Install the Agent Skills-compatible skill with the `skills` CLI:

```bash
npx skills add kenviriya/Full-team-AGILE
```

### OpenCode

Install the Agent Skills-compatible skill with the `skills` CLI:

```bash
npx skills add kenviriya/Full-team-AGILE
```

Or add the repository directly to `opencode.json`:

```json
{
  "plugin": ["github:kenviriya/Full-team-AGILE"]
}
```

## Use

Invoke the installed skill directly:

```text
/full-team-agile:feature Add saved searches to the dashboard.
```

The workflow persists artifacts under the vault-relative `Features/<workspace-name>/<feature-id>/` path in the configured Obsidian MCP Vault, never beneath the repository checkout. At feature start it treats the invocation root as a container and discovers only non-symlinked immediate-child Git repositories whose canonical root is that exact canonical child. It never follows child symlinks or recursively includes nested repositories. A Git repository at the container root is excluded unless the request identifies it and the user confirms it for the current session; its state path is `.`. New runs generate and print a readable unique feature ID (for example, `saved-searches--20260721t153045z--a1b2c3d4`):

1. Product manager asks focused questions and writes `01-prd.md`.
2. UX writes `02-ui-spec.md` only when the PRD changes a user-facing surface.
3. Before implementation, repository selection uses explicit repository name/path first, then explicit cross-repository scope, current directory, active file, and finally the sole eligible child. Current-directory and active-file inference resolve the nearest canonical Git root and use it only when that exact root was discovered, so an undiscovered nested repository never selects its parent. Explicit scope overrides editor context; ambiguous requests at a multi-repository container root ask instead of guessing. Invalid, stale, nested-undiscovered, outside-workspace, unselected, and unconfirmed-root targets are rejected before lifecycle Git actions. For each selected repository, the skill creates and checks out its own `feature/<feature-id>` branch and applies the existing safeguards independently: if the target already exists and the tree is dirty, it blocks before checkout; occupied worktrees block; and destructive reset requires separate confirmation. Backend and frontend engineers receive one workspace-relative repository assignment at a time and cannot infer or touch siblings.
4. Explicit cross-repository work uses a separate delegation and Git lifecycle for each authorized repository. State records relative paths and isolated policy, branch/base metadata, changed files, checks, temporary artifacts, cleanup, and local/remote deletion outcomes. Results are reported by repository path as success, failure, skip, rejection, or unavailability; one repository's failure never authorizes an action in another.
5. QA validates acceptance criteria separately in each recorded repository and writes repository-keyed evidence to `04-test-report.md`. Failures return only that repository to implementation.
6. Code review evaluates each QA-passing repository and writes repository-keyed `03-review-notes.md`. On approval, only explicitly tracked temporary artifacts are removed within their owning repository immediately before completion. Local and remote branch deletion remain separate, fresh, repository-qualified opt-ins and retain all clean-tree, ownership, policy, worktree, merged-only, exact-ref, and non-force safeguards.

Different feature IDs cannot perform concurrent source edits in one checkout. Non-mutating stages may proceed; serialize source changes and tests that share repository resources.

Resume a saved feature with the printed ID:

```text
/full-team-agile:feature continue <feature-id>
```

Legacy simple-slug feature folders remain resumable. If a legacy state has no current-checkout workspace metadata, the skill stops and asks the user before mutating it; it never moves uncommitted work automatically. On completion, the branch remains for the user to commit, merge, and manage.

The bundled agents are also available for targeted delegation when only one phase is needed.

### Configure agent models (Claude Code)

Each bundled agent keeps its frontmatter default unless a higher-precedence mapping is usable. Resolution happens immediately before every delegation in this order: invocation → saved feature → repository → user/global → bundled default.

The native Claude aliases `sonnet`, `opus`, `haiku`, and `fable` use Claude Code's normal `Agent` delegation. Other non-empty model IDs are classified as gateway routes and can be used by an integration host through the included OpenAI-compatible protocol runner. The runner is configured only with standard environment variables:

```bash
export OPENAI_BASE_URL="https://gateway.example"
export OPENAI_API_KEY="..."
```

Gateway model IDs are opaque strings: the plugin does not maintain provider-specific model lists.

| Agent | Bundled default |
| --- | --- |
| `product-manager` | `haiku` |
| `ux-designer` | `sonnet` |
| `backend-engineer` | `opus` |
| `frontend-engineer` | `opus` |
| `qa-engineer` | `sonnet` |
| `code-reviewer` | `opus` |

Set the plugin's `agent_models` option to a JSON object for user/global defaults:

```json
{
  "pluginConfigs": {
    "full-team-agile@full-team-agile": {
      "options": {
        "agent_models": "{\"product-manager\":\"anthropic/claude-haiku\",\"backend-engineer\":\"provider/custom-model\"}"
      }
    }
  }
}
```

Repository overrides use each selected `<repository-root>/.claude/full-team-agile.json`; delegations launch with that repository as their working directory, so sibling mappings remain isolated:

```json
{
  "agentModels": {
    "frontend-engineer": "provider/frontend-model",
    "qa-engineer": "provider/test-model"
  }
}
```

An empty repository mapping (`agentModels: {}`) is valid and preserved exactly:

```json
{
  "agentModels": {}
}
```

Supply a current-run override by adding `agent-models=<JSON object>` to the `/full-team-agile:feature` invocation. Add `persist-agent-models` to save that mapping in the feature's `State.md`; resumed runs reload it. Native aliases are passed through a private prompt envelope that the `PreToolUse` hook removes before the delegate sees it. Gateway model IDs are identified by the feature workflow instead of being passed to Claude Code's native `Agent` field.

A gateway run uses non-streaming OpenAI-compatible Chat Completions tool calling. The external model can request only normalized `read`, `glob`, `grep`, `bash`, `write`, and `edit` operations. The included runner does not execute shell or filesystem operations. An integration host must verify the recorded checkout, execute approved native tools, and return sanitized results to complete a tool loop. Claude Code plugins do not currently provide that host bridge, so gateway routes are not executable through the bundled `/full-team-agile:feature` workflow. Unknown tools and paths outside the recorded checkout must be denied by any integration host.

Gateway protocol runs stop after completion, unrecoverable error, 25 model turns, or 10 minutes. An integration host should stop on a denied or failed host action and retain completed edits rather than roll them back. `OPENAI_API_KEY`, authorization headers, gateway request bodies, and transcripts are never written to feature state, artifacts, normal status output, or error messages. Native aliases work without gateway environment variables.

Unknown agents, malformed mappings, and non-string or empty values warn without blocking other agents. The plugin prints the repository/user/bundled baseline once when its Claude Code session starts and does not repeat it for each delegation.

### Claude Code requirements

The full workflow requires Claude Code with the Obsidian MCP tools and Git branch support because it reads and writes feature state and artifacts in the Obsidian Vault. The portable skill is available to Codex, Kimi Code, and OpenCode, but those hosts need compatible agent delegation, Obsidian MCP support, and Git branch management. Concurrent source edits in one checkout must fail closed; non-mutating stages may still run.

### Optional workflow integrations

For visually expressive user-facing work, the skill uses `design-taste-frontend` when available. This integration is optional; routine product UI and backend work do not require it.

## Develop locally

Run Claude Code with the plugin directory:

```bash
claude --plugin-dir /home/ken/Personal/Code/Full-team-AGILE
```

Validate the manifests before publishing:

```bash
cd /home/ken/Personal/Code/Full-team-AGILE
claude plugin validate
```

## Update

```text
/plugin marketplace update full-team-agile
```

```text
/plugin update full-team-agile@full-team-agile
```

## License

[MIT](LICENSE).
