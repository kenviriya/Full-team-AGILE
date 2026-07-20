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

The workflow persists artifacts under `Features/<repo-name>/<slug>/` in the Obsidian Vault:

1. Product manager asks focused questions and writes `01-prd.md`.
2. UX writes `02-ui-spec.md` only when the PRD changes a user-facing surface.
3. Backend and frontend engineers implement only the applicable work; they run in parallel only when their changes are independent.
4. QA validates acceptance criteria and writes `04-test-report.md`. Failures return the work to implementation.
5. Code review writes `03-review-notes.md`. Requested changes return the work to implementation; approval completes the feature.

Resume a saved feature with:

```text
/full-team-agile:feature continue <slug>
```

The bundled agents are also available for targeted delegation when only one phase is needed.

### Claude Code requirements

The full workflow requires Claude Code with the Obsidian MCP tools because it reads and writes the feature state and artifacts in the Obsidian Vault. The portable skill is available to Codex, Kimi Code, and OpenCode, but those hosts need compatible agent delegation and Obsidian MCP support to run the complete resumable workflow.

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
