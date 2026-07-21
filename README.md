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

The workflow persists artifacts under `Features/<repo-name>/<feature-id>/` in the Obsidian Vault. New runs generate and print a readable unique feature ID (for example, `saved-searches--20260721t153045z--a1b2c3d4`):

1. Product manager asks focused questions and writes `01-prd.md`.
2. UX writes `02-ui-spec.md` only when the PRD changes a user-facing surface.
3. Before implementation, the skill creates one Git branch and worktree for the feature. Backend and frontend engineers implement only the applicable work; they run in parallel only when their ownership is disjoint and they share no contract, schema, migration, generated output, lockfile, fixture, configuration, or test resource.
4. QA validates acceptance criteria in that feature worktree and writes `04-test-report.md`. Failures return the work to implementation.
5. Code review evaluates that feature worktree and writes `03-review-notes.md`. Requested changes return the work to implementation; approval completes the feature.

Different feature IDs may progress concurrently only in their own recorded worktrees. Worktrees isolate source changes, not shared databases, ports, caches, credentials, or other test resources; serialize tests or report a blocker when those resources cannot run independently.

Resume a saved feature with the printed ID:

```text
/full-team-agile:feature continue <feature-id>
```

Legacy simple-slug feature folders remain resumable. If a legacy state has no worktree metadata, the skill asks whether to continue it exclusively in place or adopt worktree isolation; it never moves uncommitted work automatically. On completion, the branch and worktree remain for the user to commit, merge, and clean up.

The bundled agents are also available for targeted delegation when only one phase is needed.

### Claude Code requirements

The full workflow requires Claude Code with the Obsidian MCP tools and Git worktree support because it reads and writes feature state and artifacts in the Obsidian Vault and isolates concurrent implementation work. The portable skill is available to Codex, Kimi Code, and OpenCode, but those hosts need compatible agent delegation, Obsidian MCP support, and Git worktree management to run concurrent implementation. Without worktree support, they must fail closed for concurrent source edits; non-mutating stages may still run.

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
