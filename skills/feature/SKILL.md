---
name: feature
description: Runs a feature through stakeholder agreement, approved PRD, builder tickets, ticket branches, optional UX, implementation, testing, and review with resumable state.
license: MIT
---

# Feature delivery

When invoked as `/feature <description>` or `/feature continue <feature-id>`:

Invocation arguments: $ARGUMENTS. New and continuing features accept `dispatchMode=serial|parallel` and `executionMode=worktree|branch`. For every new feature, ask for dispatch mode and then execution mode even when arguments or configuration provide defaults; persist both before lifecycle Git mutation or delegation. On continuation, reread State.md and reject conflicting supplied modes. `dispatchMode` controls scheduling only. `executionMode` controls ticket Git isolation. Never infer either from repository count or agent count.

## State contract

1. Capture the invocation workspace root before repository discovery. Preserve a non-Git parent as the multi-repository container and artifact identity. Durable artifacts use Obsidian MCP vault tools only. The feature directory is `<artifact-root>/Features/<workspace-name>/<feature-id>/`; `<artifact-root>` is vault-relative, never an OS path.
2. Discover only canonical, non-symlinked immediate-child primary Git checkouts. Accept a child only when `git rev-parse --show-toplevel` resolves to that exact child, its real `.git` is a directory, and its resolved Git directory is that `.git`. Reject linked worktrees, `.claude/worktrees`, nested repositories, symlink escapes, and duplicates before state lookup or lifecycle Git actions.
3. Select repositories before State.md lookup, creation, policy loading, or lifecycle Git commands. Priority is freshly validated coordinator scope, explicit path/name, explicit cross-repository scope, current directory, active file, then sole eligible child. Explicit scope overrides editor context. Reject the whole invalid scope without sibling fallback. Treat a Git repository at the container root as path `.` and require explicit identification plus fresh session confirmation.
4. Generate and print a unique `<feature-id>` from a readable slug, lowercase UTC timestamp, and random suffix. Validate supplied and continued IDs against `^[a-z0-9]+(?:-+[a-z0-9]+)*$`; never reuse a feature directory.
5. New features create State.md as **version 6** with `artifactRoot`, `stage: questions`, `executionMode`, `dispatchMode`, `prdApproval`, feature-level `artifacts`, `agentModels`, `history`, workspace identity, ordered repository discovery/selection, a repository object keyed by workspace-relative path, and an ordered `tickets` object keyed by ticket ID. State.md is authoritative and must be reread before every resume, allocation, dispatch, or stage advance.
6. `prdApproval` records at least `status: pending|approved`, the exact approved `01-prd.md` revision/hash, approval time, and approval history. Never infer approval from prior discussion, ticket existence, or legacy state. Any PRD content change invalidates approval and returns the workflow to `prd-approval` after revision and any newly required discovery.
7. Each ticket state records its artifact path, immutable ID and slug, repository path/key, builder role, `dependsOn`, referenced PRD criteria, status, dependency depth, dependency-PR guidance, branch, base commit and source, runtime, worktree ownership, changed files, checks, blockers, temporary artifacts, QA/review outcomes, and cleanup outcome. Ticket prose stays in its Obsidian artifact; State.md keeps compact execution data.
8. Each selected repository record owns canonical root, policy, preview/base identity, allocation outcomes, and ordered ticket IDs. Never use absolute repository identity as a State object key. Resolve every stored path from the current workspace root and repeat eligibility and selected-membership validation before mutation; mark stale or moved records unavailable rather than remapping them.
9. `temporaryArtifacts` under a ticket are the only deletion authority for that ticket. Register normalized repository-relative files before creation with kind, creator, time, and active status. Reject directories, duplicates, `..`, paths outside the ticket runtime, and durable Vault artifacts. Never infer ownership later.
10. Read each selected repository's `.claude/full-team-agile.json` independently at workspace creation and cleanup. Persist optional `protectedBranches`; malformed policy blocks deletion only for that repository. Configuration reads never rewrite `agentModels`, including `{}`.
11. One session controls one feature ID. If it is active elsewhere, stop unless the user explicitly takes over after the prior session is inactive.
12. Version-6 continuations reuse persisted approval, ticket IDs, sequence allocations, branches, bases, dependency tips, statuses, and cleanup records without renumbering or inference.
13. Existing **version-5** features continue through their recorded PRD-centric, feature-branch lifecycle under the version-5 contract. Do not fabricate approval or tickets and do not migrate them to version 6. Existing version-2 through version-4 migrations retain their legacy rules and must reach version 5, not version 6.

## Product agreement

The product manager operates in workflow-selected modes:

- **discovery:** ask only questions material to scope, behavior, measurable success, product policy, or material cost/risk. After each stakeholder answer, reconsider the whole proposal and ask newly exposed material follow-ups. Continue until none remain. Technical questions belong here only when they change business behavior, cost, policy, or risk.
- **prd-draft/revision:** write a concise PRD with stable acceptance-criterion IDs (`AC-01`, `AC-02`, ...), no unresolved material questions, and explicit in-scope/out-of-scope boundaries. Save the draft as `<feature-directory>/01-prd.md` through Obsidian MCP.
- **ticket-decomposition:** only after approval of the exact PRD revision, split approved scope into the smallest independently testable builder deliverables. Tickets may be assigned only to `backend-engineer` or `frontend-engineer`; QA and review are workflow gates, not tickets. Do not invent scope.

Present every PRD draft to the stakeholder and wait for an affirmative approval of that exact revision. Feedback returns to discovery when it exposes a material question, otherwise to PRD revision. No UX artifact, ticket allocation, Git workspace, or builder delegation may occur while approval is pending.

## Ticket identity and allocation

Derive a repository key from the selected repository basename: uppercase it, replace every run of non-alphanumeric characters with `-`, collapse and trim separators, and reject an empty result. Example: `pas-services` becomes `PAS-SERVICES`.

Allocate each ticket's zero-padded repository-wide number through `<artifact-root>/Features/<workspace-name>/_ticket-sequences/<repository-key>.md` using Obsidian MCP. Read the current counter, calculate the next unused number, revalidate the exact previously read counter immediately before persistence, and update only that value. Fail closed on a concurrent change, malformed record, or existing ticket/artifact/local branch/worktree collision; never reuse or silently skip an allocated identity. Allocation order is the PM's approved deterministic ticket order.

A ticket uses:

```text
id: PAS-SERVICES-001
artifact: tickets/PAS-SERVICES-001-user-auth.md
branch: feature/PAS-SERVICES-001-user-auth
```

Each ticket artifact records ID, repository, exactly one builder role, `dependsOn`, referenced `AC-XX` criteria, outcome, scope, expected validation, out-of-scope boundaries, and dependency-PR guidance when stacked. The approved PRD is authoritative read-only context; the optional UI specification is supplementary. Validate that every stable PRD criterion is covered by at least one ticket and every ticket references at least one applicable criterion before Git setup.

Dependencies must be acyclic and necessary. Dependency depth counts tickets in the chain; permit at most three tickets (`A → B → C`). Reject deeper decomposition and return to stakeholder replanning. Prefer an independently mergeable enabling/stub ticket or an explicitly approved feature-flag boundary when a large prerequisite would create a deeper stack. Every stacked ticket persists: `Depends on <prerequisite ticket/PR>; do not merge until it is merged`. This is guidance for later manual PRs; the workflow never creates or inspects a PR.

## Ticket workspace contract

One ticket owns one short-lived branch. The feature workflow owns branch/worktree creation; builders never mutate Git topology. Before creating a ticket runtime, display and persist repository root, current branch, clean/dirty status, ticket ID, planned branch, planned base commit, and base source.

A ticket with no dependencies branches from the repository's recorded feature base commit. A dependent ticket branches from the exact recorded committed tip of its prerequisite ticket branch after that prerequisite has passed its required implementation gate. Verify that the tip differs from or validly descends from the prerequisite base and record the full SHA. Because this workflow never commits, transfers uncommitted changes, merges, or rebases, pause for user action while a prerequisite lacks a user-created commit containing its work. Never substitute the primary checkout HEAD or another ticket's tip.

For `executionMode=branch`, use the clean selected primary checkout and serialize all same-repository ticket work. Before creation, require an empty `git status --porcelain`, the expected starting branch/base, and no local branch or worktree collision. Create only:

```text
git -C <primary-checkout> switch -c feature/<ticket-id>-<slug> <ticket-base-commit>
```

Record `worktree: null`, the primary checkout as runtime, the return branch, and plugin ownership. A later ticket cannot start until the current ticket's branch work is committed as required, the primary checkout is clean, and the workflow safely returns to the recorded repository starting branch. Never reset, stash, force, adopt, or discard work.

For `executionMode=worktree`, create a deterministic plugin-owned runtime outside the primary checkout:

```text
<primary-checkout-parent>/.full-team-agile/worktrees/<repository-name>/<feature-id>/<ticket-id>
```

Validate that the path is beneath that exact plugin root, has no symlink parent, does not exist, and is not registered. Require a clean primary checkout and create only:

```text
git -C <primary-checkout> worktree add -b feature/<ticket-id>-<slug> <ticket-worktree-path> <ticket-base-commit>
```

Record exact canonical path, branch, base, `pluginOwned: true`, and active status. On continuation require the same registered path, branch, repository, gitdir form, ownership, and base relationship. Never adopt, recreate, relocate, or fall back from a missing or mismatched runtime.

Immediately before every source edit, QA run, review, or cleanup, validate the selected repository, recorded ticket runtime, canonical Git root, exact branch, base ancestry, worktree registration when applicable, and operation boundary. File tools use absolute paths beneath the runtime; Git uses `git -C <recorded-runtime>`; non-Git commands may use only command-local `cd -- <recorded-runtime> && ...`. Reject `..`, symlink, canonical, or command escapes. Expected uncommitted ticket changes are allowed for QA/review but not branch creation, switching, or optional deletion.

A ticket is dispatchable only when its dependencies are complete, its exact required base tip is recorded and available, its runtime can be established, and ownership/resource checks pass. `serial` runs one ready ticket at a time. `parallel` may run dependency-ready tickets only in valid distinct plugin-owned worktrees with disjoint ownership and no shared schema, migration, generated artifact, lockfile, configuration, fixture, or external test resource. Branch mode always serializes same-repository tickets. Different repositories remain independently isolated.

Never automatically commit, push, create or inspect pull requests, poll CI, merge, rebase, tag, release, or delete a branch.

## Agent model configuration

Supported keys are `product-manager`, `ux-designer`, `backend-engineer`, `frontend-engineer`, `qa-engineer`, and `code-reviewer`. Resolve non-empty model strings immediately before delegation in this order: invocation mapping, State.md feature mapping, selected repository `.claude/full-team-agile.json`, user/global option, bundled frontmatter. Warn and skip malformed mappings, unknown agents, and invalid values without changing other entries or configuration.

For native `sonnet`, `opus`, `haiku`, or `fable`, append the private resolver envelope with the selected canonical primary repository plus nonempty invocation/feature mappings. The hook removes it and sets the model. Other IDs are gateway routes and require an external integration host; the bundled workflow stops before delegation. Never persist gateway credentials, headers, request bodies, or transcripts.

## Delegation contract

Every builder, QA, and review delegation receives exactly one ticket: State.md reference, ticket artifact, approved PRD, optional UI spec, ticket ID, referenced criteria, dependency/base data, one selected workspace-relative repository, canonical primary root, recorded runtime, exact branch/base commit, allowed ownership, and ticket-specific evidence. Native Agent cwd is untrusted. The delegate verifies all recorded boundaries and never infers or touches siblings, other tickets, or another runtime.

Builders implement only their assigned ticket. They report ticket ID, changed files, checks, blockers, temporary-artifact requests, and evidence for each referenced PRD criterion. A failed ticket returns to the same builder ticket; the PM does not create a fix ticket.

QA independently validates one implemented ticket branch/runtime at a time and writes ticket-keyed evidence rolled up to PRD criteria in `04-test-report.md`. Review independently examines one QA-passing ticket branch/runtime at a time and writes ticket-keyed findings and PRD traceability in `03-review-notes.md`. Neither evaluates an implied merged feature tree.

Before UX or frontend delegation, consider only skills in that agent's declared `skills` frontmatter. Match only skills in that list, ordered by the most direct purpose match for the delegated task, the strongest match for the feature's UI/UX needs, the most specific documented purpose, then the lexicographically earliest declared skill name. Select at most one, persist its name and reason, and do not scan or dynamically load skills. If no frontmatter-declared skill is applicable, select none and record one warning. Do not perform this matching for product, backend, QA, or review work. Resolve conflicts in this order: user request and approved PRD; repository conventions and existing UI patterns; selected skill; bundled Full-team-AGILE guidance.

## Stage routing

- **questions:** run PM discovery; present material questions and wait. Repeat after every answer until none remain.
- **prd:** run PM PRD drafting/revision, save `01-prd.md`, set `prdApproval.status: pending`, and advance to **prd-approval**.
- **prd-approval:** present the exact draft revision and wait. Affirmative approval records that revision and advances to **ux-check**. Feedback returns to **questions** or **prd**. Perform no UX, ticket, Git, or builder action here.
- **ux-check:** inspect the approved PRD. Route user-facing screen, interaction, state, or accessibility work to **ux**; otherwise route to **tickets**. `designTaste` is true only for expressive surfaces.
- **ux:** delegate `ux-designer`, save `02-ui-spec.md`, then advance to **tickets**.
- **tickets:** run PM ticket decomposition, validate PRD coverage/dependencies/depth, allocate repository sequence IDs, save ticket artifacts below `tickets/`, persist ticket state, then advance to **implementation**. No Git setup occurs before all ticket artifacts are valid.
- **implementation:** establish and dispatch only ready ticket runtimes. Delegate exactly one ticket to its assigned builder, persist its result, and repeat until every ticket is implemented or blocked. Pause when stacked work needs a user-created prerequisite commit. Then advance to **testing**.
- **testing:** delegate QA separately for each implemented ticket in its recorded runtime. Save ticket-keyed and PRD-rolled-up `04-test-report.md`. FAIL returns only that ticket to **implementation**; never review it.
- **review:** delegate review separately for each QA-passing ticket. Save ticket-keyed `03-review-notes.md`. Requested changes return only that ticket to **implementation**; approved tickets advance to **cleanup**.
- **cleanup:** remove only registered temporary artifacts within each owning ticket runtime. For a clean, inactive, approved, matching plugin-owned ticket worktree, run non-force `git worktree remove` and then `git worktree prune`; otherwise retain it and record why. Always retain ticket branches unless a separate repository-qualified deletion flow is explicitly requested and every existing ownership, protection, clean-tree, merged-only, exact-ref, and non-force safeguard passes. Cleanup failure blocks only its ticket and prevents terminal success.
- **ready-for-integration:** enter only after every ticket independently passes QA, review, and required cleanup. Do not call the feature integrated or done.

## Ready for integration

List every approved ticket ID, artifact, repository path, branch, base commit/source, QA/review evidence, and cleanup outcome in deterministic order. State explicitly that these independently approved ticket branches are **not an integrated feature tree** and that integrated validation remains pending external user-managed commits, pushes, PRs, CI, dependency-order merges, and final integration testing. The feature directory is the audit trail. Do not direct the release workflow to release this feature until external integration is complete.
