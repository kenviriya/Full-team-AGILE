---
name: feature
description: Runs a feature through the full AI-SDLC pipeline — PM Q&A, optional UX, implementation, testing, review — with resumable, isolated state per feature.
license: MIT
---

# Feature delivery

When invoked as `/feature <description>` or `/feature continue <feature-id>`:

## State contract

1. Determine the canonical repository root and name before entering a worktree:
   ```sh
   repo_root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
   repo_name=$(basename "$repo_root")
   ```
2. For a new feature, create and immediately print a unique readable `<feature-id>` from the description slug, lowercase UTC timestamp, and short random suffix; never reuse a feature folder.
3. For continuation, validate the exact supplied ID against `^[a-z0-9]+(?:-+[a-z0-9]+)*$` before using it in a Vault path, worktree path, or branch name. Reject `/`, `.`, whitespace, and all other characters.
4. Read `Features/<repo-name>/<feature-id>/State.md` with `mcp__obsidian__read_note`; if absent, create it with `mcp__obsidian__write_note`:
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
5. State.md is authoritative. Reread it before every resume or stage advance; after a stage, overwrite it with the next stage, timestamp, artifact paths, compact outcome (including changed files/checks/failures where applicable), and history. Do not duplicate artifact contents or rely on conversation memory.
6. One session controls one feature ID. If it is active elsewhere, stop and ask the user to confirm takeover after the prior session is inactive. An overwrite-only state note is not an atomic lock.
7. If mutation needs a legacy state without `version: 2` or workspace metadata, stop and ask whether to continue exclusively in the current checkout or adopt a worktree. Never move uncommitted work automatically.

## Workspace contract

Before the first source-mutating stage, capture and display this repository/workspace preview before creating a branch or worktree:

```text
repository name: <repo-name>
repository root: <repo-root>
current branch: <current branch>
base commit: <current full HEAD SHA>
working tree: clean|dirty
planned branch: feature/<feature-id>
planned worktree: <repo-root>/.claude/worktrees/<feature-id>
```

Persist that preview under `workspacePreview` in State.md, including when it was displayed and whether creation succeeded, failed, or was blocked. Immediately before creation, re-check the final repository root, branch, and full HEAD SHA against the preview. If any differs, stop without creating a branch or worktree, report the mismatch, and persist it in State.md. Do not delegate implementation until a matching preview is created successfully.

When the re-check matches, create and record one workspace:

```text
branch: feature/<feature-id>
worktree: <repo-root>/.claude/worktrees/<feature-id>
baseCommit: <current full HEAD SHA>
```

Persist the actual branch, worktree, and base commit under `workspace` in State.md. Record any creation failure in State.md and do not delegate implementation. On continuation, reuse a valid recorded workspace only; never silently recreate a missing or mismatched one. Before every implementation, testing, or review delegation, verify the assigned directory, `git rev-parse --show-toplevel`, checked-out branch, and base commit all match State.md; missing or mismatched metadata stops work rather than recreating an unknown workspace.

Different feature IDs require separate recorded worktrees. Without worktree management, fail closed for concurrent source edits; non-mutating stages may proceed. Never automatically commit, merge, delete a worktree, or delete its branch.

## Delegation contract

Every delegate receives the State.md reference, applicable artifact keys, and only its task-specific delta. Implementation handoff also supplies the persisted repository root, worktree, branch, base commit, and relevant workspace-preview/creation status; the implementation agent must recheck them and refuse to edit on a mismatch. Mutating delegates also receive allowed ownership scope; QA receives implementation changed files and `git status --short`; review additionally receives QA evidence. Agents verify and operate only in the recorded workspace.

Implementation reports changed files, checks, assumptions, and blockers for State.md. QA and review are independent non-mutating gates. Keep UX/frontend conditional; do not implement with material unresolved requirements. Load optional design guidance only when `designTaste` is true, a compatible skill is available, and the work is visually expressive.

Run backend/frontend lanes in parallel only with disjoint ownership and no shared contract, schema, migration, generated artifact, lockfile, configuration, fixture, or external test resource; otherwise serialize them. Parallel tests likewise require independently runnable repository resources.

## Stage routing

- **questions:** `product-manager` identifies only questions material to scope, behavior, success criteria, or risk. Present them and wait for answers.
- **prd:** `product-manager` receives the idea and answers. Save its concise, acceptance-criteria-based PRD as `Features/<repo-name>/<feature-id>/01-prd.md`, then advance to **ux-check**.
- **ux-check:** Read `01-prd.md`. Route to **ux** only for a user-facing screen, interaction, state, or accessibility change; otherwise route to **implementation**. Set `designTaste: true` only for expressive work such as a landing page, portfolio, marketing surface, or major redesign; default to `false` for routine product UI.
- **ux:** Delegate to `ux-designer`; provide compatible guidance when enabled. Save `Features/<repo-name>/<feature-id>/02-ui-spec.md`, then advance to **implementation**.
- **implementation:** Delegate applicable server/API/database work to `backend-engineer` and client/component/accessibility work to `frontend-engineer` under the delegation contract. Record reported changed files and checks, then advance to **testing**.
- **testing:** Delegate to `qa-engineer`. Save `Features/<repo-name>/<feature-id>/04-test-report.md`; on any FAIL, record failures and return to **implementation**. Never proceed to review after a failed QA report.
- **review:** Delegate to `code-reviewer`. Save `Features/<repo-name>/<feature-id>/03-review-notes.md`; requested changes return to **implementation**, approval sets **done**.

## Done

On `done`, summarize what was built and list State.md's artifact paths, branch, worktree path, and base commit. State that the feature folder is the audit trail and commit, merge, integration, and worktree cleanup remain the user's responsibility.
