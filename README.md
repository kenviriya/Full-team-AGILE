# Full-team-AGILE

A compact Claude Code plugin that moves a software feature from requirements to an independently reviewed implementation.

It ships one feature-pipeline skill and four focused agents:

| Item | Use it for |
| --- | --- |
| `feature-pipeline` skill | Coordinating product, UX, implementation, and review for a feature request. |
| `agile-product-manager` | Turning an idea into a concise PRD with testable acceptance criteria. |
| `agile-ux` | Producing a UI specification when an approved feature has a user-facing surface. |
| `agile-implementer` | Implementing an approved PRD and optional UI spec with repository-native patterns. |
| `agile-reviewer` | Independently reviewing the completed implementation without editing it. |

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

Ask Claude Code to use the feature pipeline for a feature request, or invoke the installed skill directly:

```text
/full-team-agile:feature-pipeline Add saved searches to the dashboard.
```

The pipeline delegates in this order:

1. Product manager writes the PRD.
2. UX writes a UI spec only when the PRD has a user-facing surface.
3. Implementer changes the code and runs relevant checks.
4. Reviewer independently checks the result against the accepted artifacts.

The bundled agents are also available for targeted delegation when only one phase is needed.

### Optional workflow integrations

When loaded in the active session, the feature pipeline uses Context Mode for efficient repository exploration and long-output analysis. For user-facing work, it uses Taste Skill through `design-taste-frontend` (`design-taste-frontend-v1` is also supported). Both integrations are optional; the pipeline works normally without them.

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
