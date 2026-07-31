# Full-team-AGILE

A Claude Code plugin for delivering a feature through product definition, conditional UX, targeted implementation, QA, and independent review. Feature state and artifacts are stored in the Obsidian Vault so work can resume across sessions.

It ships `feature`, `sprint`, and `release` skills plus six focused agents:

| Item | Use it for |
| --- | --- |
| `feature` skill | Orchestrating one feature from questions through QA and review, with durable state. |
| `sprint` skill | Coordinating a dependency-safe backlog through isolated feature runs and a final integration gate. |
| `release` skill | Releasing a completed sprint by default, or an explicit completed feature, with preflight and confirmation. |
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

`feature` and `sprint` accept `executionMode=worktree|branch` on new and continue invocations. `executionMode` controls Git isolation: `worktree` preserves isolated plugin-owned worktrees, while `branch` makes the feature workflow own safe branch creation and checkout in the clean primary checkout without creating worktrees. For a new run that omits `executionMode`, the plugin uses a valid `default_execution_mode` option and otherwise safely falls back to `worktree`; an explicit command value wins. Continuations always preserve the State.md execution mode, so a later configuration change cannot alter in-flight work. Every new feature and sprint also always asks whether to use `dispatchMode=serial|parallel`, even when an invocation includes a mode argument. `serial` runs one eligible unit at a time; `parallel` permits concurrency only when all existing dependency, scope, worktree, ownership, contract, and resource checks approve it. The scheduling choice never relaxes Git safety.

Coordinate a sprint backlog with dependency-safe feature runs:

```text
/full-team-agile:sprint Deliver saved searches, including API, dashboard UI, and documentation.
/full-team-agile:sprint executionMode=branch Deliver saved searches, including API, dashboard UI, and documentation.
/full-team-agile:sprint dispatchMode=parallel Deliver saved searches, including API, dashboard UI, and documentation.
```

The plugin is a resumable AI delivery workflow: specialized agents define, design, implement, test, and independently review work; durable Obsidian-vault artifacts preserve progress across sessions. Feature delivery owns repository and branch safety, sprint coordinates dependencies and integration, and release performs confirmed release mutations only.

### Sprint

Sprint coordination persists `Sprints/<workspace-name>/<sprint-id>/` in the configured Obsidian MCP vault, not the active Git workspace. A sprint may start from a non-Git parent folder, which it preserves as a multi-repository workspace container for artifact identity. Sprint discovers eligible immediate-child primary checkouts read-only, inspects concrete item evidence, and automatically passes an unambiguous single- or multi-repository scope to its `feature` workflow; it asks when evidence is missing, weak, conflicting, cross-repository scope is uncertain, or the container root `.` would be required. The feature workflow freshly validates every supplied path and remains the authority for repository selection, Git, branches, worktrees, QA, review, cleanup, and artifacts. Sprint never implies all child repositories, mutates repositories, or repairs a rejected delegate runtime. It decomposes the backlog into feature-sized items, dispatching one eligible item at a time in serial mode or dependency-safe disjoint lanes as `feature` workflows in parallel mode; parallel work remains subject to the same repository, isolation, ownership, contract, and resource safeguards. Each delegated feature workflow routes its own specialized lifecycle agents; sprint never replaces that workflow's Git, QA, review, or cleanup lifecycle. Sprint writes `03-sprint-recap.md` for every terminal sprint outcome; successful integration checks are recorded in `02-integration-report.md`. A done sprint is eligible for an explicit `release` workflow; sprint itself does not merge, tag, or push.

### Release

Release defaults to a completed sprint:

```text
/full-team-agile:release <sprint-id> version=1.2.3 target=main remote=origin
```

Release one completed feature only with the explicit feature form. For multi-repository work, select workspace-relative repositories explicitly (or use `repositories=all`):

```text
/full-team-agile:release feature <feature-id> version=1.2.3 target=main remote=origin repositories=apps/api,apps/web
```

A release requires an explicit SemVer version, target branch, and remote. It saves `Releases/<workspace-name>/<release-id>/` in the configured Obsidian MCP vault, not the active Git workspace, preflights recorded commits and clean trees, then asks for fresh confirmation before creating release branches, merging, validating, tagging, advancing the target, and pushing the exact target branch and annotated tag. It pushes after confirmed local success by default. Package publication and GitHub Releases remain disabled unless separately requested with a repository-qualified command or policy and separately confirmed. Resume an incomplete release with `/full-team-agile:release continue <release-id>`; it revalidates state and resumes only incomplete work. Release never infers `main` or multi-repository scope, stages arbitrary work, stashes, resets, force-pushes, deletes branches or tags, or automatically rolls back.

### Feature lifecycle

The feature workflow persists artifacts under `Features/<workspace-name>/<feature-id>/` in the configured Obsidian MCP vault, never as a project-relative filesystem folder. At feature start it treats the invocation root as a container and discovers only non-symlinked immediate-child **primary** Git checkouts: each candidate must have a real `.git` directory that resolves to that exact canonical child. It rejects linked worktrees, including `.claude/worktrees/...`, never follows child symlinks, and never recursively includes nested repositories. A Git repository at the container root is excluded unless the request identifies it and the user confirms it for the current session; its state path is `.`. New runs generate and print a readable unique feature ID (for example, `saved-searches--20260721t153045z--a1b2c3d4`):

1. Product manager asks focused questions and writes `01-prd.md`.
2. UX writes `02-ui-spec.md` only when the PRD changes a user-facing surface.
3. Before implementation, repository selection uses explicit repository name/path first, then explicit cross-repository scope, current directory, active file, and finally the sole eligible child. Current-directory and active-file inference resolve the nearest canonical Git root and use it only when that exact root was discovered, so an undiscovered nested repository never selects its parent. Explicit scope overrides editor context; ambiguous requests at a multi-repository container root ask instead of guessing. Invalid, stale, linked-worktree, `.claude/worktrees`, nested-undiscovered, outside-workspace, unselected, and unconfirmed-root targets are rejected before lifecycle Git actions. For each selected repository, choose the persisted execution mode. In `worktree` mode, the skill creates one deterministic plugin-owned Git worktree outside the primary checkout at `.full-team-agile/worktrees/<repository-name>/<feature-id>` and a matching `feature/<feature-id>` branch; State.md records the exact worktree path, branch, ownership, and cleanup status. In `branch` mode, the skill requires a clean primary checkout, creates a new `feature/<feature-id>` branch without creating a worktree, and records `worktree: null` plus the primary checkout as runtime; it never adopts an unowned existing branch. Existing legacy records are migrated only after their ownership/runtime metadata is validated. Immediately before source edits, every delegate validates its recorded runtime path, Git root, branch, worktree registration when applicable, and base relationship explicitly. Native Agent may inherit the multi-repository container cwd; that cwd is not trusted or required to match. File operations use absolute paths beneath the recorded runtime, Git uses `git -C <recorded-runtime>`, and non-Git commands use an explicit command-local `cd` only when needed. A mismatch or escape is refused before edits without automatic relocation, repair, adoption, reset, or sibling fallback; branch or path collisions block before mutation. Backend and frontend engineers receive one workspace-relative repository assignment at a time and cannot infer or touch siblings. The persisted `dispatchMode` controls only eligible concurrent delegation: `serial` runs implementation and independently runnable tests one at a time; `parallel` still requires disjoint ownership and independently safe resources.
4. Explicit cross-repository work uses a separate delegation and Git lifecycle for each authorized repository. State records relative paths and isolated policy, branch/base metadata, changed files, checks, temporary artifacts, cleanup, and local/remote deletion outcomes. Results are reported by repository path as success, failure, skip, rejection, or unavailability; one repository's failure never authorizes an action in another.
5. QA validates acceptance criteria separately in each recorded repository and writes repository-keyed evidence to `04-test-report.md`. Failures return only that repository to implementation.
6. Code review evaluates each QA-passing repository and writes repository-keyed `03-review-notes.md`. On approval, only explicitly tracked temporary artifacts are removed within their owning recorded runtime path immediately before completion. A clean, matching, inactive plugin-owned worktree is then automatically removed and pruned; dirty, external, mismatched, active, blocked, failed, or awaiting-input worktrees are retained with a recorded reason. The feature branch is retained by default. Local and remote branch deletion remain separate, fresh, repository-qualified opt-ins with all clean-tree, ownership, policy, worktree, merged-only, exact-ref, and non-force safeguards.

Different feature IDs may perform same-repository source edits concurrently only through distinct valid plugin-owned worktrees and pairwise-disjoint ownership/resources; otherwise the workflow serializes them. Non-mutating stages may proceed independently.

Resume a saved feature with the printed ID:

```text
/full-team-agile:feature continue <feature-id>
```

Legacy simple-slug feature folders remain resumable. A valid legacy primary-checkout record uses an explicit `executionMode` choice when supplied and otherwise persists the safe `worktree` default before mutation; missing or malformed checkout metadata, or ambiguous worktree metadata, stops for user resolution. The workflow never moves uncommitted work automatically. On completion, the branch remains for the user to commit, merge, and manage.

The bundled agents are also available for targeted delegation when only one phase is needed.

### Configure artifact storage (Claude Code)

Durable feature, sprint, and release files are read and written with Obsidian MCP vault tools. They are never created relative to the active Git workspace. With the Obsidian MCP vault rooted at `/Users/kenviriya/Code/Claude-Brain`, the default `artifact_root` of `""` produces:

```text
Features/<workspace-name>/<feature-id>/
Sprints/<workspace-name>/<sprint-id>/
Releases/<workspace-name>/<release-id>/
```

inside that vault. Set `artifact_root` only to a validated vault-relative parent directory when needed; for example, `"MVPVaults"` produces `MVPVaults/Features/...`, `MVPVaults/Sprints/...`, and `MVPVaults/Releases/...`. It is not an OS path and must not include `Features`, `Sprints`, or `Releases` itself.

```json
{
  "pluginConfigs": {
    "full-team-agile@full-team-agile": {
      "options": {
        "artifact_root": "MVPVaults"
      }
    }
  }
}
```

New State.md files record `artifactRoot`. On continuation, the recorded State.md location remains authoritative; the workflow can find legacy root-level records for compatibility but never moves or relocates artifacts automatically.

### Configure default execution mode (Claude Code)

Set `default_execution_mode` to `worktree` (the safe default) or `branch` to choose the Git isolation mode for **new** `feature` and `sprint` runs that omit `executionMode`:

```json
{
  "pluginConfigs": {
    "full-team-agile@full-team-agile": {
      "options": {
        "default_execution_mode": "branch"
      }
    }
  }
}
```

Resolution is explicit `executionMode` argument → persisted State.md mode for a continuation → valid `default_execution_mode` → `worktree`. Empty or invalid option values warn and use `worktree`. This setting is independent of `dispatchMode` and never changes an existing workflow.

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
