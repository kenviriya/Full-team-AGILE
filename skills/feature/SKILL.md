---
name: feature
description: Runs a feature through the full AI-SDLC pipeline — PM Q&A, optional UX, implementation, testing, review — with resumable, isolated state per feature.
license: MIT
---

# Feature delivery

When invoked as `/feature <description>` or `/feature continue <feature-id>`:

## State contract

1. Determine the canonical repository root and name in the current checkout:
   ```sh
   repo_root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
   repo_name=$(basename "$repo_root")
   ```
2. For a new feature, create and immediately print a unique readable `<feature-id>` from the description slug, lowercase UTC timestamp, and short random suffix; never reuse a feature folder.
3. For continuation, validate the exact supplied ID against `^[a-z0-9]+(?:-+[a-z0-9]+)*$` before using it in a Vault path or branch name. Reject `/`, `.`, whitespace, and all other characters.
4. Read `Features/<repo-name>/<feature-id>/State.md` with `mcp__obsidian__read_note`; if absent, create it with `mcp__obsidian__write_note`:
   ```json
   {
     "version": 2,
     "featureId": "<feature-id>",
     "stage": "questions",
     "repository": { "name": "<repo-name>", "root": "<repo-root>" },
     "repositoryPolicy": { "source": "<repository-root>/.claude/full-team-agile.json", "protectedBranches": [], "valid": true },
     "artifacts": {},
     "temporaryArtifacts": [],
     "cleanup": { "status": "pending", "attempts": [] },
     "history": []
   }
   ```
5. State.md is authoritative. Reread it before every resume or stage advance; after a stage, overwrite it with the next stage, timestamp, artifact paths, compact outcome (including changed files/checks/failures where applicable), `agentModels.feature` when supplied, cleanup status, repository policy, and history. Do not duplicate artifact contents or rely on conversation memory. Missing `temporaryArtifacts` or `cleanup` fields in an existing version-2 state mean an empty registry and pending cleanup; missing `repositoryPolicy` means no protected feature branches and records that default before cleanup.
6. `temporaryArtifacts` is the only deletion authority for plugin- or agent-created temporary files. Before creating one, record its normalized repository-relative path, `kind` (`test` or `execution`), `createdBy`, `recordedAt`, and `status: "active"`; reject directories, paths outside the recorded root, `..` paths, duplicates, and durable Vault artifacts. Update its status after cleanup. Never infer ownership from Git status, path names, extensions, locations, or an after-the-fact claim.
7. Parse an invocation-scoped agent mapping only when the invocation includes `agent-models=<JSON object>`. For a new feature, optionally persist it as `agentModels.feature` when the invocation also includes `persist-agent-models`; on continuation, reload that persisted mapping. Invocation mappings otherwise apply only to the current invocation and are never written to State.md.
8. At workspace creation and again before cleanup, read `<repository-root>/.claude/full-team-agile.json` for an optional `protectedBranches` array of non-empty branch names. Persist it as `repositoryPolicy` with `source: "<repository-root>/.claude/full-team-agile.json"` and `valid: true`; an absent file or field persists `protectedBranches: []`. A malformed or unreadable policy persists `valid: false` with its source, blocks requested branch deletion, and records the validation failure; never assume an unreadable policy leaves a branch unprotected.
9. One session controls one feature ID. If it is active elsewhere, stop and ask the user to confirm takeover after the prior session is inactive. An overwrite-only state note is not an atomic lock.
10. If mutation needs a legacy state without `version: 2` or current-checkout workspace metadata, stop and ask the user to confirm continuing in the current checkout. Never move uncommitted work automatically.

## Workspace contract

Before the first source-mutating stage, capture and display this repository/workspace preview before creating a branch:

```text
repository name: <repo-name>
repository root: <repo-root>
current branch: <current branch>
base commit: <current full HEAD SHA>
working tree: clean|dirty
planned branch: feature/<feature-id>
```

Persist that preview under `workspacePreview` in State.md, including when it was displayed and whether creation succeeded, failed, or was blocked. Immediately before creation, re-check the final repository root, branch, and full HEAD SHA against the preview. If any differs, stop without creating a branch, report the mismatch, and persist it in State.md.

If the working tree is dirty and `feature/<feature-id>` does not exist, ask once whether to create it from the configured remote `main` reference (default `origin/main`; use an existing configured remote when provided). Declining preserves the current branch and uncommitted work and records creation as blocked. If accepted, use `git checkout -b feature/<feature-id> <remote-main>` without `--force`; otherwise use the preview base commit. Treat Git's ordinary checkout refusal as a blocked creation: do not stash, discard, reset, or force checkout.

If `feature/<feature-id>` already exists, first inspect `git worktree list --porcelain`. If another registered worktree has `branch refs/heads/feature/<feature-id>`, block without changing branches or files. Otherwise, if the tree is dirty, block before checkout and preserve the current branch and uncommitted work; the user may clean or stash manually, then rerun. Never stash, discard, reset, or force checkout automatically. For a clean tree, request a separate explicit destructive-reset confirmation before switching; state that resetting `feature/<feature-id>` to `<remote-main>` will discard commits on that branch. Do not infer this confirmation from any remote-main or branch-creation confirmation. After confirmation, first verify that `<remote-main>` resolves to a commit; if it does not, record creation as blocked and leave the current branch untouched. Only then may `git checkout feature/<feature-id>` followed by `git reset --hard <remote-main>` run. Declining records creation as blocked and leaves the branch and files untouched.

Record one workspace. When the plugin creates the branch, also record the branch checked out immediately before creation as `returnBranch` and `branchCreatedByPlugin: true`; otherwise record `branchCreatedByPlugin: false`.

```text
root: <repo-root>
branch: feature/<feature-id>
baseCommit: <chosen full HEAD SHA>
returnBranch: <pre-creation branch>
branchCreatedByPlugin: true|false
```

Persist the actual root, branch, and base commit under `workspace`. Record any creation failure in State.md and do not delegate implementation. On continuation, reuse a valid recorded workspace only; never silently recreate a missing or mismatched one. Before every implementation, testing, or review delegation, verify `git rev-parse --show-toplevel`, checked-out branch, and base commit all match State.md; missing or mismatched metadata stops work rather than recreating an unknown workspace.

Different feature IDs cannot make concurrent source edits in one checkout; non-mutating stages may proceed. Never create, register, switch to, or remove a Git worktree. Never automatically commit, merge, or delete a branch; local feature-branch deletion is permitted only during the explicit cleanup stage.

## Agent model configuration

The supported keys are the six bundled agent names: `product-manager`, `ux-designer`, `backend-engineer`, `frontend-engineer`, `qa-engineer`, and `code-reviewer`. Model values are opaque non-empty strings; do not maintain an allowlist or rewrite provider/model IDs.

Resolve the model immediately before every delegation, independently for that agent, in this order:

1. Current invocation `agent-models=<JSON object>`.
2. State.md `agentModels.feature`.
3. `<repository-root>/.claude/full-team-agile.json` field `agentModels`.
4. Plugin user option `CLAUDE_PLUGIN_OPTION_AGENT_MODELS`.
5. The delegated agent's bundled frontmatter `model`.

Each mapping must be a JSON object. Warn and skip an unreadable object, unknown agent key, or value that is not a non-empty string; include scope, agent when known, and the rejected value without affecting other entries. Never edit bundled frontmatter.

Immediately before each bundled-agent delegation, reread State.md and the repository configuration and resolve the selected model from all five scopes.

- For `sonnet`, `opus`, `haiku`, or `fable`, append this private resolver envelope to the native Agent tool call (omit empty scopes):

  ```text
  <!-- full-team-agile-agent-models: {"invocation":<current invocation object>,"feature":<State.md agentModels.feature object>} -->
  ```

  The plugin's `PreToolUse` hook removes the envelope and sets the resolved native alias in the Agent input. It does not auto-approve the call.
- For every other non-empty model ID, do not invoke the native Agent tool. The bundled Claude Code workflow must report that gateway routes need an external integration host and stop before delegation; Claude Code plugin hooks cannot host the required tool loop. `scripts/gateway-agent.py` is a protocol runner for such a host, using `OPENAI_BASE_URL` and `OPENAI_API_KEY` only at request time.
- An external integration host may process a gateway tool request only after revalidating the recorded checkout root, branch, and base commit; it must reject unknown tools and paths outside the recorded checkout, invoke matching user-approved tools, and return sanitized results. The runner must never execute repository actions itself.
- The protocol runner limits a gateway integration to normal completion, unrecoverable error, 25 model turns, or 10 elapsed minutes. An external host must stop on a tool denial/failure, retain completed edits without rollback, and record only compact outcome metadata (route, model, turns, terminal reason, changed files), never gateway credentials, headers, request bodies, or transcripts.

At plugin/session start, parse the user/global and repository mappings and display one baseline entry per bundled agent (repository → user/global → bundled default), including whether it routes to native or gateway, plus warnings. Do this once per plugin/session, not before each delegation.

## Delegation contract

Every delegate receives the State.md reference, applicable artifact keys, and only its task-specific delta. Implementation handoff also supplies the persisted repository root, branch, base commit, and relevant workspace-preview/creation status; the implementation agent must recheck them and refuse to edit on a mismatch. Mutating delegates also receive allowed ownership scope; QA receives implementation changed files and `git status --short`; review additionally receives QA evidence. Agents verify and operate only in the recorded checkout. Before any implementation or QA delegate creates a temporary test or execution file, it must report the path and kind for State.md registration; it must report the same path as a blocker if registration cannot occur. Delegates must not remove or claim ownership of any unregistered file.

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
- **review:** Delegate to `code-reviewer`. Save `Features/<repo-name>/<feature-id>/03-review-notes.md`; requested changes return to **implementation**, approval advances to **cleanup**.
- **cleanup:** Run immediately before the final completion response. Reread State.md and validate the recorded repository root. For every active `temporaryArtifacts` entry only, resolve it beneath that root without following symlinks: reject a symlink in any parent path, then remove a regular file or unlink a final symlink; record `removed` or `alreadyAbsent`. Reject directories, invalid/outside-root paths, and unexpected file types. Any validation or deletion failure records a blocked cleanup attempt, leaves the feature in **cleanup**, and prevents a done claim. Durable Vault records (`State.md`, PRD, UI spec, QA report, and review notes) are never temporary artifacts.

  Local feature-branch deletion is optional and requires a new final confirmation that names both `feature/<feature-id>` and `returnBranch`. If it is not requested, record `branchRetained` and continue. Before evaluating deletion, reread and validate `repositoryPolicy.protectedBranches`; an absent persisted policy must first be populated from `<repository-root>/.claude/full-team-agile.json`, and an invalid or unreadable policy blocks deletion. If requested, proceed only if `branchCreatedByPlugin` is true, the recorded branch exactly equals `feature/<feature-id>`, that branch is not in the persisted protected-branch policy, the return branch exists and differs, the checkout is clean, no other registered worktree has the feature branch checked out, and the branch is fully merged. Then `git switch <returnBranch>` and run only `git branch -d <feature-branch>`. Never force-delete, stash, reset, or remove a worktree. An unsafe condition or deletion failure is a blocked cleanup result; retain the branch and do not report done.

  Remote deletion is separately optional. It requires another new final confirmation naming `feature/<feature-id>` and remote; local-deletion confirmation never authorizes it. Before evaluating deletion, reread and validate `repositoryPolicy.protectedBranches`; an absent persisted policy must first be populated from `<repository-root>/.claude/full-team-agile.json`, and an invalid or unreadable policy blocks deletion. If requested, proceed only if `branchCreatedByPlugin` is true, the recorded branch exactly equals `feature/<feature-id>`, that branch is not in the persisted protected-branch policy, the named remote is recorded/configured, and the remote feature ref exists. Delete only that ref with `git push <remote> --delete <feature-branch>`. Never delete a remote protected or unrelated branch, and do not treat a remote-deletion decline as a local-deletion decline. Record the local and remote outcomes independently.
- **done:** Only after cleanup succeeds, summarize completion.

## Done

On `done`, summarize what was built and list State.md's artifact paths, checkout root, branch, and base commit. State that the feature folder is the audit trail and commit, merge, and integration remain the user's responsibility. Include the recorded cleanup outcome; if optional branch deletion was not requested, say the branch was retained.
