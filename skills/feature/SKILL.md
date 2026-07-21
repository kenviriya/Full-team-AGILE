---
name: feature
description: Runs a feature through the full AI-SDLC pipeline — PM Q&A, optional UX, implementation, testing, review — with resumable, isolated state per feature.
license: MIT
---

# Feature delivery

When invoked as `/feature <description>` or `/feature continue <feature-id>`:

## Feature identity and state

1. Determine the canonical repository root and name before entering a worktree:
   ```sh
   repo_root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
   repo_name=$(basename "$repo_root")
   ```
2. For a new feature, create a readable unique `<feature-id>` from the description slug, a lowercase UTC timestamp, and a short random suffix, for example `saved-searches--20260721t153045z--a1b2c3d4`. Print it immediately. Do not reuse an existing folder for a new invocation.
3. For continuation, accept the supplied value as the exact `<feature-id>` only after validating it matches `^[a-z0-9]+(?:-+[a-z0-9]+)*$`. Reject IDs containing `/`, `.`, whitespace, or any other characters before using them in a Vault path, worktree path, or branch name. Simple legacy slugs remain valid IDs.
4. Read `Features/<repo-name>/<feature-id>/State.md` from the Obsidian Vault with `mcp__obsidian__read_note`. If it does not exist, create it with `mcp__obsidian__write_note`:
   ```json
   {
     "version": 2,
     "featureId": "<feature-id>",
     "stage": "questions",
     "repository": { "name": "<repo-name>", "root": "<repo-root>" },
     "artifacts": {},
     "history": []
   }
   ```
5. Always reread the state note before resuming or advancing a stage. After a completed stage, overwrite it with the next stage, timestamp, artifact paths, stage outcome, and a history entry. Never keep feature state only in conversation memory.
6. One session controls one feature ID at a time. If a continuation finds the feature already actively in progress elsewhere, stop and ask the user to confirm takeover after the prior session is inactive. An overwrite-only state note is not an atomic lock.
7. If a legacy state lacks `version: 2` or workspace metadata when mutation is needed, stop and ask the user whether to continue it exclusively in the current checkout or adopt a worktree. Never move uncommitted work automatically.

## Workspace isolation

Before the first mutating stage, create and record one worktree and branch for the feature from an immutable base commit:

```text
branch: feature/<feature-id>
worktree: <repo-root>/.claude/worktrees/<feature-id>
baseCommit: <current HEAD SHA>
```

Persist them under `workspace` in `State.md`:

```json
{
  "workspace": {
    "path": "<worktree-path>",
    "branch": "feature/<feature-id>",
    "baseCommit": "<sha>"
  }
}
```

Before every implementation, testing, and review delegation, verify that the assigned directory, `git rev-parse --show-toplevel`, checked-out branch, and recorded base commit match the state. On continuation, reuse the recorded workspace. If it is absent or mismatched, stop rather than recreating it from an unknown revision.

Do not run concurrent implementation in a host that cannot create and manage Git worktrees. Non-mutating stages may proceed, but fail closed for concurrent source edits. Do not commit, merge, delete the worktree, or delete the branch automatically; completion leaves integration and cleanup to the user.

## Stages

- **questions:** Delegate to `product-manager` to identify questions that materially affect scope, behavior, success criteria, or risk. Present those questions directly to the user and wait for answers.
- **prd:** Delegate to `product-manager` with the idea and answers. Save its concise, acceptance-criteria-based PRD to `Features/<repo-name>/<feature-id>/01-prd.md`.
- **ux-check:** Read `01-prd.md`. If it changes a user-facing screen, interaction, state, or accessibility behavior, continue to **ux**; otherwise, skip to **implementation**. Set `designTaste: true` only for visually expressive work such as a landing page, portfolio, marketing surface, or major redesign; default to `false` for routine product UI.
- **ux:** If `designTaste` is true and `design-taste-frontend` is available, load its relevant visual guidance. Delegate to `ux-designer` with `01-prd.md` and the guidance when available. Save the UI specification to `Features/<repo-name>/<feature-id>/02-ui-spec.md`.
- **implementation:** Read the PRD and optional UI specification. Delegate applicable server-side/API/database work to `backend-engineer` and client-side/component/accessibility work to `frontend-engineer`. Include the feature ID, assigned worktree, branch, base commit, allowed file scope, and prior stage artifacts in every handoff. Run the lanes in parallel only when their intended ownership is disjoint and they share no API contract, schema, migration, generated artifact, lockfile, configuration, fixture, or external test resource; otherwise run them serially in the same feature worktree. Include design-taste guidance for visually expressive frontend work. Save reported changed files and checks in state.
- **testing:** Delegate to `qa-engineer` with the source artifacts, assigned worktree, branch, base commit, implementation-reported changed files, and `git status --short`. QA must evaluate only that workspace; include untracked files in scope. Save the report to `Features/<repo-name>/<feature-id>/04-test-report.md`. Concurrent tests are allowed only when repository test resources are independently runnable; otherwise serialize them or report a blocker. On any FAIL, record failures in state and return to **implementation** with failure notes. Do not proceed to review after a failed QA report.
- **review:** Delegate to `code-reviewer` with the source artifacts, assigned worktree, branch, base commit, implementation-reported changed files, `git status --short`, and QA evidence. Review only that workspace. Save notes to `Features/<repo-name>/<feature-id>/03-review-notes.md`. On changes requested, return to **implementation** with the notes. On approval, set the stage to `done`.

## Boundaries

- Different feature IDs may progress concurrently only in separate recorded worktrees.
- Keep UX and frontend work conditional; do not invoke them for backend-only changes.
- Use optional design-taste guidance only when the active session provides it and the feature needs expressive visual direction.
- Do not begin implementation while unresolved requirements materially affect behavior.
- QA and review are independent gates; neither silently edits implementation.
- Keep artifacts concise and scoped to the feature. Avoid process documents for trivial changes.

## Done

On `done`, summarize what was built, list the Obsidian Vault artifact paths, branch, worktree path, and base commit. State that the feature folder is the audit trail and that commit, merge, and worktree cleanup remain the user's responsibility.
