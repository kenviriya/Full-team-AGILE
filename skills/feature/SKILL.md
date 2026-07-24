---
name: feature
description: Runs a feature through the full AI-SDLC pipeline — PM Q&A, optional UX, implementation, testing, review — with resumable, isolated state per feature.
license: MIT
---

# Feature delivery

When invoked as `/feature <description>` or `/feature continue <feature-id>`:

## State contract

1. Capture the invocation workspace root before repository discovery. Use its basename as `<workspace-name>` for the vault-relative feature artifact root `Features/<workspace-name>/<feature-id>/`; do not replace it with a selected child name. Read and write `State.md` and every feature artifact at that root through the Obsidian MCP tools. Do not resolve this path under the workspace checkout or create a checkout-local `Features/` copy. A feature uses one artifact backend only: when Obsidian MCP is unavailable, record the artifact operation as unavailable and stop the affected stage rather than silently falling back to the filesystem.
2. Inspect only the canonical workspace root's immediate child directories. Exclude symlinked child paths. For each remaining child run `git -C <child> rev-parse --show-toplevel`; accept it only when the canonical returned Git root equals that exact canonical child and its parent equals the canonical workspace root. This accepts normal repositories and linked-worktree `.git` files, excludes symlink escapes and nested descendants, normalizes/deduplicates roots, and stores each as a workspace-relative path. Do not run Git against a candidate after this eligibility check until selection succeeds.
3. Select before State.md lookup, creation, policy loading, or lifecycle Git commands, in this priority: explicit repository path or name; explicit named cross-repository scope; current directory; active file; sole eligible child. Explicit scope overrides inferred context. For current-directory or active-file inference, resolve the location's nearest canonical Git root with `git rev-parse --show-toplevel` and select it only when that exact root is eligible; never map a nested repository to its eligible parent. An active file outside the workspace or inside an intentionally undiscovered nested repository supplies no target. At a multi-repository container root, or for any ambiguous request, ask instead of guessing and execute no lifecycle Git command.
4. Treat the workspace root as a container even when it is a Git repository. Select `.` only when explicit request or context identifies the root and the user gives session-scoped confirmation. Never persist that confirmation for a future session.
5. Reject invalid, ambiguous, stale, removed, unselected, outside-workspace, nested-undiscovered, or unconfirmed-root targets before State.md or repository Git activity. A cross-repository task is authorized only by explicit repository names or an explicit request for all already-selected repositories; never default to all detected children.
6. For a new feature, create and immediately print a unique readable `<feature-id>` from the description slug, lowercase UTC timestamp, and short random suffix; never reuse a feature folder. For continuation, validate the exact ID against `^[a-z0-9]+(?:-+[a-z0-9]+)*$`; reject `/`, `.`, whitespace, and all other characters.
7. Read the vault-relative `Features/<workspace-name>/<feature-id>/State.md` through Obsidian MCP; if absent, create version 3 with feature-level `artifacts`, `agentModels`, and `history`, plus `workspace.root`, ordered `detectedRepositories`, ordered `selectedRepositories`, and a `repositories` object keyed by normalized workspace-relative path (`api`, `web`, or confirmed `.`). Only feature `full-semi-auto-full-approval-cleanup-obsidian-prd-20260724073110-a7f3` may additionally store the `featureSessionAuthorization` defined below. Each repository record owns its canonical root, `repositoryPolicy`, `workspacePreview`, checkout `workspace`, `temporaryArtifacts`, `cleanup`, changed files, checks, failures, and compact outcomes. Never store absolute repository identity as the key.
8. State.md is authoritative. Reread it through Obsidian MCP before every resume or stage advance. Resolve every stored repository-relative path from the current workspace root and repeat canonical eligibility and selected-membership validation; mark a removed, moved, nested, or otherwise ineligible record unavailable and never transfer its metadata to another repository. Preserve ordered per-repository outcomes.
9. `temporaryArtifacts` in each repository record is the only deletion authority for that repository. Before creating one, record its normalized repository-relative path, `kind` (`test` or `execution`), `createdBy`, `recordedAt`, and `status: "active"`; reject directories, paths outside that repository root, `..`, duplicates within the record, and durable Vault artifacts. Identical relative paths in sibling records remain independent. Never infer ownership after the fact.
10. Parse invocation and persisted agent mappings as documented below. Repository discovery, state creation, migration, delegation, and cleanup must read configuration without rewriting it; `agentModels: {}` is valid and must remain untouched.
11. At workspace creation and before cleanup or deletion, read each selected repository's `.claude/full-team-agile.json` independently. Persist its optional `protectedBranches` under that repository record. Missing file/field means `[]`; malformed or unreadable policy sets `valid: false` and blocks deletion only for that repository.
12. One session controls one feature ID. If active elsewhere, stop and ask for takeover only after the prior session is inactive.
13. Migrate version-2 single-repository state only when its recorded canonical root equals the active workspace root. Map it to repository key `.`, preserve feature-level fields and existing lifecycle metadata beneath that record, and require fresh session-scoped root confirmation before any root Git action. Block stale/mismatched roots and all other legacy mutation rather than remapping them. Never move uncommitted work automatically.

## Feature-session authorization

This section is an exception only for feature ID `full-semi-auto-full-approval-cleanup-obsidian-prd-20260724073110-a7f3`. No other feature ID may create, activate, copy, inherit, or interpret `featureSessionAuthorization`; ignore such metadata for every other feature. For the named feature, accept the authorization only when the current invocation or continuation targets that exact ID and the user supplied it in the current feature session. Normalize it under feature-level `featureSessionAuthorization` with `featureId: "full-semi-auto-full-approval-cleanup-obsidian-prd-20260724073110-a7f3"`, `scope: "feature-session"`, the authorization time, and explicit booleans `noPlanMode`, `contextMode`, `obsidianPrdWrite`, and `registeredTemporaryArtifactCleanup`. Before every use, require both the active feature ID and metadata `featureId` to equal that exact ID and require current-session reauthorization; otherwise the metadata authorizes nothing. Missing or false fields authorize nothing. Never treat persisted metadata as authorization for a later session, copy it to another feature, or write it to repository-local settings, global settings, or agent configuration.

When `noPlanMode` is authorized, the host and every delegate must execute the applicable feature stage directly and must not invoke or request plan mode. This changes workflow routing only; it grants no tool permission and does not suppress material questions or blockers.

When `contextMode` or `obsidianPrdWrite` is authorized, perform applicable Context Mode operations and write the approved PRD to its recorded Obsidian artifact destination without asking the user for an additional workflow approval where the platform permits. Treat `obsidianPrdWrite` as authorization only for the approved PRD artifact of this feature, not arbitrary Vault content. External permission prompts and tool availability are host-owned: the plugin cannot bypass, auto-answer, or claim success over a platform denial or unavailable operation. Preserve the platform decision, record `success`, `failed`, `rejected`, or `unavailable` with compact evidence in State.md, and stop or continue according to the affected stage's existing contract.

When `registeredTemporaryArtifactCleanup` is authorized, it satisfies only the workflow approval to run cleanup for active entries already registered in each repository's `temporaryArtifacts`. It never authorizes discovering, registering after creation, or deleting any other path, durable Vault artifact, branch, worktree, or remote ref. All cleanup validation, symlink and repository-boundary checks, repository policy, and separate local/remote branch confirmations remain mandatory. No feature-session authorization may override platform permission decisions or any destructive safeguard in this skill.

Pass only the applicable normalized authorization fields to each delegate as task context, including the feature-session scope and the instruction that platform decisions prevail. Do not represent the metadata as host permission configuration or claim that it pre-approves native Agent, Context Mode, Obsidian, filesystem, shell, Git, or other tool calls.

## Workspace contract

For each selected repository, capture and display this repository/workspace preview before creating its branch:

```text
repository name: <repo-name>
repository root: <repo-root>
current branch: <current branch>
base commit: <current full HEAD SHA>
working tree: clean|dirty
planned branch: feature/<feature-id>
```

Persist that preview under the selected repository record's `workspacePreview`, including when it was displayed and whether creation succeeded, failed, or was blocked. Immediately before creation, revalidate the workspace-relative path, canonical Git root, selected membership, root confirmation when path is `.`, final branch, and full HEAD SHA against the preview. If any differs, stop only that repository operation, report the mismatch, and persist it.

If the working tree is dirty and `feature/<feature-id>` does not exist, ask once whether to create it from the configured remote `main` reference (default `origin/main`; use an existing configured remote when provided). Declining preserves the current branch and uncommitted work and records creation as blocked. If accepted, use `git checkout -b feature/<feature-id> <remote-main>` without `--force`; otherwise use the preview base commit. Treat Git's ordinary checkout refusal as a blocked creation: do not stash, discard, reset, or force checkout.

If `feature/<feature-id>` already exists, first inspect `git worktree list --porcelain`. If another registered worktree has `branch refs/heads/feature/<feature-id>`, block without changing branches or files. Otherwise, if the tree is dirty, block before checkout and preserve the current branch and uncommitted work; the user may clean or stash manually, then rerun. Never stash, discard, reset, or force checkout automatically. For a clean tree, request a separate explicit destructive-reset confirmation before switching; state that resetting `feature/<feature-id>` to `<remote-main>` will discard commits on that branch. Do not infer this confirmation from any remote-main or branch-creation confirmation. After confirmation, first verify that `<remote-main>` resolves to a commit; if it does not, record creation as blocked and leave the current branch untouched. Only then may `git checkout feature/<feature-id>` followed by `git reset --hard <remote-main>` run. Declining records creation as blocked and leaves the branch and files untouched.

Record one checkout lifecycle per selected repository. When the plugin creates a branch, also record the branch checked out immediately before creation as `returnBranch` and `branchCreatedByPlugin: true`; otherwise record `branchCreatedByPlugin: false`.

```text
root: <repo-root>
branch: feature/<feature-id>
baseCommit: <chosen full HEAD SHA>
returnBranch: <pre-creation branch>
branchCreatedByPlugin: true|false
```

Persist the actual root, branch, and base commit beneath that repository record's `workspace`. Record creation failures independently and do not delegate implementation for a failed repository. On continuation, reuse only valid recorded repository workspaces; never silently recreate a missing or mismatched one. Before every implementation, testing, review, or cleanup delegation, revalidate the relative path, canonical root, selected membership, root confirmation, checked-out branch, and recorded base relationship. A mismatch stops that repository rather than authorizing work elsewhere.

Run every Git command with the resolved repository as explicit `cwd` or `git -C <repository-root>` target. An explicitly cross-repository request executes the complete Git, policy, cleanup, and reporting lifecycle separately in deterministic selected-path order. Record each result by workspace-relative path as `success`, `failed`, `skipped`, `rejected`, or `unavailable`; one repository's failure never authorizes, rolls back, or changes another repository's operation.

Different feature IDs cannot make concurrent source edits in the same selected checkout; non-mutating stages may proceed. Never create, register, switch to, or remove a Git worktree. Never automatically commit, merge, or delete a branch; local feature-branch deletion is permitted only during the explicit cleanup stage.

## Agent model configuration

The supported keys are the six bundled agent names: `product-manager`, `ux-designer`, `backend-engineer`, `frontend-engineer`, `qa-engineer`, and `code-reviewer`. Model values are opaque non-empty strings; do not maintain an allowlist or rewrite provider/model IDs.

Resolve the model immediately before every delegation, independently for that agent, in this order:

1. Current invocation `agent-models=<JSON object>`.
2. State.md `agentModels.feature`.
3. The selected repository's `<repository-root>/.claude/full-team-agile.json` field `agentModels`.
4. Plugin user option `CLAUDE_PLUGIN_OPTION_AGENT_MODELS`.
5. The delegated agent's bundled frontmatter `model`.

Each mapping must be a JSON object. Warn and skip an unreadable object, unknown agent key, or value that is not a non-empty string; include scope, agent when known, and the rejected value without affecting other entries. Never edit bundled frontmatter.

Immediately before each bundled-agent delegation, reread State.md and the selected repository configuration, resolve the selected model from all five scopes, and launch the delegation with the selected repository as `cwd`. The existing hook then resolves that repository's configuration. `agentModels: {}` is a valid empty mapping and falls through without mutation.

- For `sonnet`, `opus`, `haiku`, or `fable`, append this private resolver envelope to the native Agent tool call (omit empty scopes):

  ```text
  <!-- full-team-agile-agent-models: {"invocation":<current invocation object>,"feature":<State.md agentModels.feature object>} -->
  ```

  The plugin's `PreToolUse` hook removes the envelope and sets the resolved native alias in the Agent input. It does not auto-approve the call.
- For every other non-empty model ID, do not invoke the native Agent tool. The bundled Claude Code workflow must report that gateway routes need an external integration host and stop before delegation; Claude Code plugin hooks cannot host the required tool loop. `scripts/gateway-agent.py` is a protocol runner for such a host, using `OPENAI_BASE_URL` and `OPENAI_API_KEY` only at request time.
- An external integration host may process a gateway tool request only after revalidating the recorded checkout root, branch, and base commit; it must reject unknown tools and paths outside the recorded checkout, invoke matching user-approved tools, and return sanitized results. The runner must never execute repository actions itself.
- The protocol runner limits a gateway integration to normal completion, unrecoverable error, 25 model turns, or 10 elapsed minutes. An external host must stop on a tool denial/failure, retain completed edits without rollback, and record only compact outcome metadata (route, model, turns, terminal reason, changed files), never gateway credentials, headers, request bodies, or transcripts.

At plugin/session start, parse the user/global mapping and the mapping for the repository selected by session cwd, then display one baseline entry per bundled agent (selected repository → user/global → bundled default), including whether it routes to native or gateway, plus warnings. Do this once per plugin/session, not before each delegation; delegation-time resolution still follows each selected repository `cwd`.

## Delegation contract

Every delegate receives the State.md reference, applicable artifact keys, and only its task-specific delta. Each backend, frontend, QA, or review delegation receives exactly one selected workspace-relative repository path, canonical root, branch, base commit, allowed ownership scope, and repository-specific evidence; it must verify that assignment and must not infer or touch siblings. Cross-repository work always uses a separate delegation per repository, launched with the selected repository as `cwd`, and reports outcomes under that repository's record. Implementation handoff also supplies the relevant repository workspace-preview/creation status; the implementation agent must recheck it and refuse to edit on a mismatch. QA receives that repository's implementation changed files and `git status --short`; review additionally receives that repository's QA evidence. Before any implementation or QA delegate creates a temporary test or execution file, it must report the repository-qualified path and kind for registration in that repository record; it must report the same path as a blocker if registration cannot occur. Delegates must not remove or claim ownership of any unregistered file.

Before delegating UX-spec work or approved frontend work, inspect the target delegate's declared `skills` frontmatter. This is the delegated runtime's supported skill attachment list: the host loads those skills when it starts that agent. Match only skills in that list. Do not scan directories, parse skill files as an installation format, query unsupported host operations, or attempt dynamic skill loading. A user-installed or plugin-provided skill is eligible only when it is already declared in that target delegate's `skills` list.

For each eligible skill, compare its documented purpose with the delegated task and the approved PRD's UI/UX needs, then assess the purpose's specificity. Select exactly one applicable skill by this fixed order: most direct purpose match for the delegated task; strongest match for the feature's UI/UX needs; most specific documented purpose; then lexicographically earliest declared skill name as the deterministic final tie-breaker. Record the selected skill's name, declared source, and concise selection reason in the delegation context persisted to State.md, and direct the applicable agent to use that already-loaded skill. If no frontmatter-declared skill is applicable, select none, record one warning in that delegation context, and continue with the bundled guidance and current workflow. Do not perform this matching for product, backend, QA, or review work. The applicable agent resolves conflicts in this order: user request and approved PRD; repository conventions and existing UI patterns; selected skill; bundled Full-team-AGILE guidance.

Implementation reports changed files, checks, assumptions, and blockers for State.md. QA and review are independent non-mutating gates. Keep UX/frontend conditional; do not implement with material unresolved requirements. `designTaste` still enables its compatible expressive-design guidance only for visually expressive work; it does not suppress relevant UI/UX skill discovery for routine user-facing work.

Run backend/frontend lanes in parallel only with disjoint ownership and no shared contract, schema, migration, generated artifact, lockfile, configuration, fixture, or external test resource; otherwise serialize them. Parallel tests likewise require independently runnable repository resources.

## Stage routing

- **questions:** `product-manager` identifies only questions material to scope, behavior, success criteria, or risk. Present them and wait for answers.
- **prd:** `product-manager` receives the idea and answers. Save its concise, acceptance-criteria-based PRD as `Features/<workspace-name>/<feature-id>/01-prd.md`, then advance to **ux-check**.
- **ux-check:** Read `01-prd.md`. Route to **ux** only for a user-facing screen, interaction, state, or accessibility change; otherwise route to **implementation**. Set `designTaste: true` only for expressive work such as a landing page, portfolio, marketing surface, or major redesign; default to `false` for routine product UI.
- **ux:** Match only skills declared for `ux-designer` under the delegation contract, then delegate with the selected already-loaded skill or recorded fallback warning. Save `Features/<workspace-name>/<feature-id>/02-ui-spec.md`, then advance to **implementation**.
- **implementation:** For each selected repository, delegate applicable server/API/database work to `backend-engineer` and client/component/accessibility work to `frontend-engineer` under the delegation contract. Match UI/UX guidance only for a frontend delegation and only against skills declared for `frontend-engineer`. Use separate delegation per repository, record repository-qualified changed files/checks/outcomes, then advance to **testing** after all authorized repository results are recorded.
- **testing:** Delegate `qa-engineer` separately for each implemented repository. Save shared `Features/<workspace-name>/<feature-id>/04-test-report.md` with sections keyed by workspace-relative repository path; on any FAIL, record that repository's failures and return it to **implementation**. Never proceed to review for a failed repository.
- **review:** Delegate `code-reviewer` separately for each QA-passing repository. Save shared `Features/<workspace-name>/<feature-id>/03-review-notes.md` with repository-keyed sections; requested changes return that repository to **implementation**, while approval advances it to **cleanup**.
- **cleanup:** Run immediately before the final completion response, independently for every selected repository. Reread State.md and revalidate relative path, canonical root, selected membership, root confirmation, branch/base relationship, and repository policy. For every active `temporaryArtifacts` entry in that repository record only, resolve it beneath that repository root without following symlinks: reject a symlink in any parent path, then remove a regular file or unlink a final symlink; record `removed` or `alreadyAbsent`. Reject directories, invalid/outside-root paths, and unexpected file types. Any validation or deletion failure records that repository as blocked, leaves it in **cleanup**, and prevents a global done claim. Durable Vault records are never temporary artifacts.

  Local feature-branch deletion is optional and evaluated independently per repository. It requires a new final confirmation naming the workspace-relative repository path, `feature/<feature-id>`, and `returnBranch`. If not requested, record `branchRetained` for that repository and continue. Reread its policy and proceed only if `branchCreatedByPlugin` is true, the branch exactly matches, is not protected, the return branch exists and differs, that repository checkout is clean, no other registered worktree occupies it, and it is fully merged. Then run `git switch <returnBranch>` and only `git branch -d <feature-branch>` in that repository. Never force-delete, stash, reset, or remove a worktree. A failure blocks only that repository's cleanup and cannot authorize sibling deletion.

  Remote deletion is separately optional per repository. It requires another new final confirmation naming the repository path, exact feature branch, and remote; local-deletion confirmation never authorizes it. Revalidate that repository and policy, then proceed only for a plugin-created exact unprotected feature branch and configured remote whose feature ref exists. Delete only with `git push <remote> --delete <feature-branch>` in that repository. Record local and remote outcomes independently by repository path.
- **done:** Only after cleanup succeeds, summarize completion.

## Done

On `done`, summarize what was built and list State.md's artifact paths plus every selected workspace-relative repository path, root, branch, base commit, and cleanup outcome in deterministic order. State that the feature folder is the audit trail and commit, merge, and integration remain the user's responsibility. If optional branch deletion was not requested for a repository, say its branch was retained.
