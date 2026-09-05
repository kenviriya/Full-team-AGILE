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

Install the portable Agent Skills distribution with the `skills` CLI:

```bash
npx skills add kenviriya/Full-team-AGILE
```

The native OpenCode npm package is publish-ready but is not published by this repository's development workflow. After publishing `opencode-full-team-agile`, add it to `opencode.json`:

```json
{
  "plugin": ["opencode-full-team-agile"]
}
```

For local development before publication, copy `opencode/index.js` into `.opencode/plugins/full-team-agile.js` and add `@opencode-ai/plugin` to `.opencode/package.json`; OpenCode loads local plugin files directly and installs their declared dependencies.

The npm/local plugin exposes `full_team_agile_status`, which reports the integration boundary. It includes the same `feature`, `sprint`, and `release` skills for portable reuse; OpenCode’s stable V1 plugin API does not register or transform them. It does not claim Claude-only Obsidian artifact storage, hooks, private agent-model routing, or release lifecycle execution. Use those skills only when the OpenCode setup provides compatible delegation, durable artifact storage, and Git lifecycle support.

## Use

Invoke the installed skill directly:

```text
/full-team-agile:feature Add saved searches to the dashboard.
```

`feature` and `sprint` accept optional `dispatchMode=serial|parallel` and `executionMode=worktree|branch` values on new and continue invocations. For every new feature or sprint, the workflow first asks whether to use `serial` or `parallel`, then asks whether to use `worktree` or `branch`, and persists both choices before lifecycle work; supplied values and plugin configuration do not suppress those ordered questions. `serial` runs one eligible unit at a time; `parallel` permits concurrency only when all existing dependency, scope, worktree, ownership, contract, and resource checks approve it. `executionMode` controls Git isolation: `worktree` preserves isolated plugin-owned worktrees, while `branch` makes the feature workflow own safe branch creation and checkout in the clean primary checkout without creating worktrees. Continuations reuse the persisted State.md modes and reject conflicts, so later configuration changes cannot alter in-flight work. The scheduling choice never relaxes Git safety.

Coordinate a sprint backlog with dependency-safe feature runs:

```text
/full-team-agile:sprint Deliver saved searches, including API, dashboard UI, and documentation.
/full-team-agile:sprint executionMode=branch Deliver saved searches, including API, dashboard UI, and documentation.
/full-team-agile:sprint dispatchMode=parallel Deliver saved searches, including API, dashboard UI, and documentation.
```

The plugin is a resumable AI delivery workflow: a product manager iterates with the stakeholder to an explicitly approved PRD, decomposes that scope into builder tickets, and specialized agents design, implement, test, and independently review each ticket branch. Durable Obsidian-vault artifacts preserve progress across sessions. Feature delivery owns repository, ticket identity, and branch safety; sprint coordinates feature dependencies and integration; release performs confirmed release mutations only.

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

1. The product manager asks focused business questions, reconsidering the proposal after every answer until no material scope, behavior, success, policy, cost, or risk question remains. The PM writes `01-prd.md` with stable criteria such as `AC-01`; the workflow presents that exact revision and waits for explicit stakeholder approval. Feedback returns to discovery or revision. No UX artifact, ticket allocation, Git workspace, or implementation starts before approval.
2. UX writes `02-ui-spec.md` only when the approved PRD changes a user-facing surface. The approved PRD remains authoritative; the UI specification is supplementary.
3. The PM decomposes only the approved scope into the smallest independently testable tickets for `backend-engineer` or `frontend-engineer`. QA and review remain independent gates. Each ticket references applicable PRD criteria and states outcome, scope, expected validation, dependencies, and out-of-scope boundaries.
4. Ticket identity is repository-scoped. The repository basename is uppercased and runs of non-alphanumeric characters become `-`; for example, `pas-services` becomes `PAS-SERVICES`. A collision-safe repository-wide sequence stored in the Obsidian vault produces IDs such as `PAS-SERVICES-001`, artifacts such as `tickets/PAS-SERVICES-001-user-auth.md`, and branches such as `feature/PAS-SERVICES-001-user-auth`. Concurrent counter changes or artifact/branch collisions fail closed; numbers are never reused silently.
5. The standard Git rule is **one ticket = one branch**. `executionMode=worktree` creates a deterministic plugin-owned runtime at `.full-team-agile/worktrees/<repository-name>/<feature-id>/<ticket-id>`; `executionMode=branch` uses the clean primary checkout and serializes same-repository tickets. Every delegate freshly validates the recorded repository, runtime, branch, base, ownership, and operation boundary. File operations use absolute paths beneath the runtime, Git uses `git -C <recorded-runtime>`, and commands never infer or touch sibling repositories or tickets.
6. Independent tickets branch from the repository's recorded feature base. A dependent ticket stacks from the exact recorded, user-created committed tip of its prerequisite branch; it pauses while that commit is unavailable because the workflow never commits or transfers uncommitted changes. Dependency chains are limited to three tickets (for example, A → B → C). Deeper work returns for stakeholder replanning, preferably as an independently mergeable enabling/stub ticket or an explicitly approved feature-flag boundary. Every stacked ticket records manual PR guidance: `Depends on <prerequisite ticket/PR>; do not merge until it is merged`.
7. Each ready ticket is delegated to exactly one builder. `dispatchMode=parallel` still requires dependency readiness, distinct valid worktrees, disjoint ownership, and independent contracts/resources; branch mode always serializes same-repository work. Failures return to the same builder ticket rather than creating PM fix tickets.
8. QA validates every implemented ticket in its recorded branch/runtime and rolls evidence up to PRD criteria in `04-test-report.md`. Code review independently reviews each QA-passing ticket and records ticket-keyed findings and PRD traceability in `03-review-notes.md`. Neither gate assumes a merged feature tree.
9. Cleanup removes only explicitly tracked temporary artifacts and eligible clean plugin-owned ticket worktrees. Ticket branches are retained by default. The workflow does not automate commits, pushes, pull requests, CI polling, rebases, merges, tags, releases, or branch deletion.
10. When every ticket independently passes QA and review, the terminal state is `ready-for-integration`. The final report lists the approved ticket branches and states that they are not an integrated feature tree; external commits, pushes, PRs, dependency-order merges, and integrated validation remain the user's responsibility.

Resume a saved feature with the printed ID:

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
