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

Before the first source-mutating stage, create and record one workspace from the current immutable HEAD:

```text
branch: feature/<feature-id>
worktree: <repo-root>/.claude/worktrees/<feature-id>
baseCommit: <current HEAD SHA>
```

Persist it under `workspace` in State.md. On continuation, reuse it only. Before every implementation, testing, or review delegation, verify the assigned directory, `git rev-parse --show-toplevel`, checked-out branch, and base commit all match State.md; missing or mismatched metadata stops work rather than recreating an unknown workspace.

Different feature IDs require separate recorded worktrees. Without worktree management, fail closed for concurrent source edits; non-mutating stages may proceed. Never automatically commit, merge, delete a worktree, or delete its branch.

## Delegation contract

Every delegate receives the State.md reference, applicable artifact keys, and only its task-specific delta. Mutating delegates also receive allowed ownership scope; QA receives implementation changed files and `git status --short`; review additionally receives QA evidence. Agents verify and operate only in the recorded workspace.

Before delegating UX-spec work or approved frontend work, inspect the target delegate's declared `skills` frontmatter. This is the delegated runtime's supported skill attachment list: the host loads those skills when it starts that agent. Match only skills in that list. Do not scan directories, parse skill files as an installation format, query unsupported host operations, or attempt dynamic skill loading. A user-installed or plugin-provided skill is eligible only when it is already declared in that target delegate's `skills` list.

For each eligible skill, compare its documented purpose with the delegated task and the approved PRD's UI/UX needs, then assess the purpose's specificity. Select exactly one applicable skill by this fixed order: most direct purpose match for the delegated task; strongest match for the feature's UI/UX needs; most specific documented purpose; then lexicographically earliest declared skill name as the deterministic final tie-breaker. Record the selected skill's name, declared source, and concise selection reason in the delegation context persisted to State.md, and direct the applicable agent to use that already-loaded skill. If no frontmatter-declared skill is applicable, select none, record one warning in that delegation context, and continue with the bundled guidance and current workflow. Do not perform this matching for product, backend, QA, or review work. The applicable agent resolves conflicts in this order: user request and approved PRD; repository conventions and existing UI patterns; selected skill; bundled Full-team-AGILE guidance.

Implementation reports changed files, checks, assumptions, and blockers for State.md. QA and review are independent non-mutating gates. Keep UX/frontend conditional; do not implement with material unresolved requirements. `designTaste` still enables its compatible expressive-design guidance only for visually expressive work; it does not suppress relevant UI/UX skill discovery for routine user-facing work.

Run backend/frontend lanes in parallel only with disjoint ownership and no shared contract, schema, migration, generated artifact, lockfile, configuration, fixture, or external test resource; otherwise serialize them. Parallel tests likewise require independently runnable repository resources.

## Stage routing

- **questions:** `product-manager` identifies only questions material to scope, behavior, success criteria, or risk. Present them and wait for answers.
- **prd:** `product-manager` receives the idea and answers. Save its concise, acceptance-criteria-based PRD as `Features/<repo-name>/<feature-id>/01-prd.md`, then advance to **ux-check**.
- **ux-check:** Read `01-prd.md`. Route to **ux** only for a user-facing screen, interaction, state, or accessibility change; otherwise route to **implementation**. Set `designTaste: true` only for expressive work such as a landing page, portfolio, marketing surface, or major redesign; default to `false` for routine product UI.
- **ux:** Match only skills declared for `ux-designer` under the delegation contract, then delegate with the selected already-loaded skill or recorded fallback warning. Save `Features/<repo-name>/<feature-id>/02-ui-spec.md`, then advance to **implementation**.
- **implementation:** Delegate applicable server/API/database work to `backend-engineer` and client/component/accessibility work to `frontend-engineer` under the delegation contract. Match UI/UX guidance only for the frontend delegation and only against skills declared for `frontend-engineer`. Record reported changed files and checks, then advance to **testing**.
- **testing:** Delegate to `qa-engineer`. Save `Features/<repo-name>/<feature-id>/04-test-report.md`; on any FAIL, record failures and return to **implementation**. Never proceed to review after a failed QA report.
- **review:** Delegate to `code-reviewer`. Save `Features/<repo-name>/<feature-id>/03-review-notes.md`; requested changes return to **implementation**, approval sets **done**.

## Done

On `done`, summarize what was built and list State.md's artifact paths, branch, worktree path, and base commit. State that the feature folder is the audit trail and commit, merge, integration, and worktree cleanup remain the user's responsibility.
