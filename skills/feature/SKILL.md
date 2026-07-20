---
name: feature
description: Runs a feature through the full AI-SDLC pipeline — PM Q&A, optional UX, implementation, testing, review — with resumable state per feature.
license: MIT
---

# Feature delivery

When invoked as `/feature <description>` or `/feature continue <slug>`:

1. Determine the current repository name (`<repo-name>`) with:
   ```sh
   basename $(git rev-parse --show-toplevel 2>/dev/null || pwd)
   ```
2. Slugify the description (or load the supplied slug). Read `Features/<repo-name>/<slug>/State.md` from the Obsidian Vault with `mcp__obsidian__read_note`. If it does not exist, create it with `mcp__obsidian__write_note`:
   ```json
   { "stage": "questions", "history": [] }
   ```
3. Always read the state note before resuming. After every completed stage, overwrite it with the current stage, timestamp, and artifact paths. Never keep feature state only in conversation memory.

## Stages

- **questions:** Delegate to `product-manager` to identify questions that materially affect scope, behavior, success criteria, or risk. Present those questions directly to the user and wait for answers.
- **prd:** Delegate to `product-manager` with the idea and answers. Save its concise, acceptance-criteria-based PRD to `Features/<repo-name>/<slug>/01-prd.md`.
- **ux-check:** Read `01-prd.md`. If it changes a user-facing screen, interaction, state, or accessibility behavior, continue to **ux**; otherwise, skip to **implementation**. Set `designTaste: true` only for visually expressive work such as a landing page, portfolio, marketing surface, or major redesign; default to `false` for routine product UI.
- **ux:** If `designTaste` is true and `design-taste-frontend` is available, load its relevant visual guidance. Delegate to `ux-designer` with `01-prd.md` and the guidance when available. Save the UI specification to `Features/<repo-name>/<slug>/02-ui-spec.md`.
- **implementation:** Read the PRD and optional UI specification. Delegate applicable server-side/API/database work to `backend-engineer`, client-side/component/accessibility work to `frontend-engineer`, and both in parallel only when their changes are independent. Include design-taste guidance for visually expressive frontend work.
- **testing:** Delegate to `qa-engineer` with the source artifacts and completed diff. Save the report to `Features/<repo-name>/<slug>/04-test-report.md`. On any FAIL, record the failures in state and return to **implementation** with the failure notes. Do not proceed to review after a failed QA report.
- **review:** Delegate to `code-reviewer` with the source artifacts, completed diff, and QA evidence. Save notes to `Features/<repo-name>/<slug>/03-review-notes.md`. On changes requested, return to **implementation** with the notes. On approval, set the stage to `done`.

## Boundaries

- Keep UX and frontend work conditional; do not invoke them for backend-only changes.
- Use optional design-taste guidance only when the active session provides it and the feature needs expressive visual direction.
- Do not begin implementation while unresolved requirements materially affect behavior.
- QA and review are independent gates; neither silently edits implementation.
- Keep artifacts concise and scoped to the feature. Avoid process documents for trivial changes.

## Done

On `done`, summarize what was built, list the Obsidian Vault artifact paths, and state that the feature folder is the audit trail.
