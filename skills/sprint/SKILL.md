---
name: sprint
description: Coordinates a dependency-safe sprint backlog by delegating each feature-sized item to the resumable feature workflow and gating final integration.
license: MIT
---

# Sprint delivery

When invoked as `/sprint <backlog description>` or `/sprint continue <sprint-id>`:

Invocation arguments: $ARGUMENTS. Every new or continue invocation accepts an optional `executionMode=worktree|branch`; omit it to use `worktree`. For a new sprint, persist the selected mode before dispatch. On continuation, reread State.md and migrate a legacy record missing `executionMode` before validating a supplied mode. First inspect every referenced nonterminal Feature State.md read-only: an explicit feature mode is compatible only with the same sprint mode; valid legacy plugin-owned worktree metadata implies `worktree`; and missing, invalid, or conflicting feature execution metadata is ambiguous. If any nonterminal feature is `worktree`, preserve and persist `worktree` and reject an explicit `branch` request without dispatch. If feature modes conflict or any is ambiguous, ask the user to resolve the conflict and do not dispatch or persist a different mode. Infer `branch` only when every existing nonterminal feature explicitly records `branch`; when no nonterminal feature constrains the migration, persist `worktree` for legacy sprint state unless the user explicitly selects `branch`. Persist the compatible migrated mode before mode-match validation, reject invalid or mismatched modes, and pass it unchanged to every feature delegate; never infer branch mode from absent fields.

## Coordinator boundary

1. Sprint coordinates multiple feature-sized backlog items. It does not replace `full-team-agile:feature`.
2. Every selected item is delivered by one separate agent invoking `full-team-agile:feature`. That feature workflow remains the sole authority for questions, PRD, UX, implementation, testing, review, cleanup, State.md artifacts, final repository validation and selection, Git branches, and worktree safeguards. Sprint may perform only read-only discovery of eligible immediate-child repositories and evidence-based mapping of backlog items to likely repositories; it must not load repository policy, run lifecycle Git commands, create a fallback checkout, or repair a rejected delegate runtime.
3. Each delegated feature workflow routes its own product-manager, conditional UX, backend/frontend implementation, QA, and code-review agents. Sprint must not directly delegate those lifecycle agents.
4. Sprint must not create, reset, switch, merge, delete, or clean up feature branches, worktrees, repositories, or feature artifacts. A `done` sprint may be released only through the explicit `full-team-agile:release` workflow.
5. Feature State.md is authoritative for each item's delivery status. Sprint records only its feature ID, State.md reference, compact observed outcome, dependencies, scheduling information, and integration evidence.

## State contract

1. Capture the invocation workspace root before any repository discovery and use its basename as `<workspace-name>`. A non-Git invocation parent is a multi-repository workspace container: preserve its exact root and basename for sprint artifacts; never replace either with a child repository root or name. Discover only eligible immediate child primary checkouts using the same canonical, non-symlink, real-`.git`, linked-worktree, `.claude/worktrees`, nested-repository, and path-boundary rules as `full-team-agile:feature`, and store normalized workspace-relative paths. For each item, perform read-only evidence inspection and persist its ordered likely `repositoryScope`, compact `scopeEvidence`, `scopeConfidence`, and `scopeSource` before dispatch. Pass that preserved workspace context and the evidence-backed workspace-relative scope to every feature delegate; sprint must not imply all child repositories or authorize `.` without fresh session-scoped confirmation. Durable sprint artifacts use Obsidian MCP vault tools only, never project-relative filesystem operations. Set `<sprint-directory>` to `<artifact-root>/Sprints/<workspace-name>/<sprint-id>/` (omit the prefix and slash when `artifact_root` is empty); `<artifact-root>` is the validated vault-relative parent announced at session start.
2. For a new sprint, generate and immediately print a unique readable `<sprint-id>` from the backlog slug, lowercase UTC timestamp, and short random suffix. Never reuse a sprint folder. For continuation, validate the exact ID against `^[a-z0-9]+(?:-+[a-z0-9]+)*$`; reject `/`, `.`, whitespace, and all other characters.
3. Persist `<sprint-directory>/State.md` through Obsidian MCP before dispatching any item. Write `<sprint-directory>/01-sprint-plan.md`, `<sprint-directory>/02-integration-report.md`, and `<sprint-directory>/03-sprint-recap.md` through Obsidian MCP.
4. State.md is authoritative for sprint coordination. Reread it through Obsidian MCP before planning changes, dispatch, dependency evaluation, continuation, and the integration gate. On continuation, look first at the configured path, then at legacy `Sprints/<workspace-name>/<sprint-id>/State.md` only when the configured root is nonempty; stop if both exist. A missing `artifactRoot` means `""`; once found, its recorded artifact root and exact State.md path are authoritative. Never relocate artifacts.
5. Use versioned compact state containing `sprintId`, `artifactRoot`, `executionMode`, `stage`, `workspace`, `backlog`, `detectedRepositories`, `items`, `lanes`, `integration`, and `history`. Each item stores its description, feature ID, exact feature State.md reference, status, `dependsOn`, ordered workspace-relative `repositoryScope`, compact `scopeEvidence`, `scopeConfidence` (`unambiguous` or `needs-confirmation`), `scopeSource` (`inferred` or `user-confirmed`), declared ownership/resources, lane, blockers, and compact outcome.
6. Item and sprint IDs are safe path segments. Dependencies refer only to existing item IDs. Reject self-dependencies and dependency cycles before any dispatch.
7. An item status is exactly one of `planned`, `ready`, `running`, `done`, `blocked`, `failed`, or `skipped`. Record its generated feature ID exactly once before delegation.
8. Do not copy PRDs, UI specs, review notes, branch metadata, temporary-artifact registries, or repository paths from a feature folder into sprint state.

## Planning and lanes

1. Ask only questions material to feature acceptance boundaries, dependencies, repository scope, or shared ownership/resources. Discover and inspect repositories read-only, but auto-select only when concrete evidence converges on one eligible repository or an exact concrete multi-repository set. Ask before dispatch when evidence is absent, weak, conflicting, stale, cross-repository scope is uncertain, or selecting the container root `.` would be required; never default to all children or the most likely repository.
2. Before dispatch, write `<sprint-directory>/01-sprint-plan.md` through Obsidian MCP with every item ID, feature-sized description, acceptance boundary, dependency IDs, discovered eligible repositories, evidence-backed intended repository scope, compact scope evidence/confidence/source, ownership/resources, lane, lane rationale, and planned feature invocation. A scope is a planning proposal until `feature` freshly validates it.
3. An item is `ready` only when every dependency is `done`, its repository scope is `unambiguous` or explicitly user-confirmed, and it has no unresolved planning blocker.
4. Run items concurrently only when their ownership/resources/contracts are disjoint and the execution mode permits it. In `branch` mode, any overlapping repository scopes conflict and serialize, even when declared resources are disjoint. In `worktree` mode, same-repository items may run concurrently only when the feature workflow can establish distinct valid plugin-owned worktrees and their declared ownership/resources/contracts are disjoint; unknown scope or shared repository without that isolation conflicts. Any shared path area, API/shared contract, schema/migration, generated artifact, lockfile/configuration, fixture, or external test resource also conflicts.
5. Unknown ownership, unresolved isolation, or unresolved contracts serialize work rather than allowing optimistic parallelism. Items sharing a selected repository may run together only under the preceding same-repository worktree rule.
6. Lanes are scheduling groups, not shared implementation assignments. Launch at most one feature agent per item.

## Delegation and status

1. Before dispatching, reread State.md, compute ready items, and select one pairwise-safe dispatch batch under the lane rules.
2. Before launching the batch, assign and persist each selected item's feature ID and record its launch as pending.
4. Launch one separate feature delegate per selected ready item in a single parallel dispatch. Instruct each delegate to invoke `full-team-agile:feature` with `executionMode=<sprint-execution-mode>`, the scoped requirement, sprint ID, item ID, `feature-id=<assigned-feature-id>`, the preserved workspace root, the item's evidence-backed explicit workspace-relative `repositoryScope`, scope evidence/source, dependencies already satisfied, and ownership/interface constraints. The supplied scope is an untrusted selection request: feature must freshly rediscover and validate every path, reject any invalid member without fallback, and retain its root-confirmation rule for `.`. In `branch` mode, serialize any selected items whose repository scopes overlap, regardless of disjoint resources; `worktree` mode retains the existing same-repository worktree isolation rule.
4. Record each launch result. Mark an item `running` only after its delegate starts. If a delegate does not start or is denied before a feature State.md exists, retain its assigned feature ID, return it to `ready`, record the launch failure, and retry only that same feature assignment on a later dispatch.
5. The delegate must follow the canonical feature workflow and use the item's exact recorded Feature State.md reference as its delivery record. Sprint must not bypass its questions or write its PRD.
6. A dispatch batch is a scheduling snapshot: items that become ready while it runs wait for the next readiness evaluation.
7. After a delegate reaches a reportable state, reread its referenced feature State.md and record the compact observed outcome in sprint state. If feature rejects a linked-worktree or recorded-runtime mismatch, record that rejection or block exactly as reported; Sprint must not create, select, repair, or retry another checkout automatically.
8. If an item is `failed` or `blocked`, do not dispatch a dependent item. Mark direct and transitive dependents `blocked` with the upstream item ID and reason. Continue independent ready lanes.
9. If a feature is waiting for user answers, retain the item's `running` status; it blocks only its dependents.
10. On continuation, retain feature IDs, refresh observed feature outcomes from their State.md files, and recompute readiness only for nonterminal items. Never recreate feature work automatically.

## Integration gate

1. When all items are terminal, set the sprint to `blocked` if any item is `failed`, `blocked`, or `skipped`. Do not claim completion or run a passing integration gate.
2. Run the integration gate only when every item is `done`.
3. Before the gate, reread every referenced feature State.md and verify each is done with passing QA and approved review evidence.
4. Collect relevant declared cross-item contract checks and recorded repository-specific checks. Run only integration checks relevant to the planned interactions and permitted without overriding feature safeguards.
5. Write commands, pass/fail evidence, impacted items, and failures to `<sprint-directory>/02-integration-report.md` through Obsidian MCP.
6. Mark the sprint `done` only when every required integration check passes. A failed check marks the sprint `failed`; do not automatically roll back, reopen, merge, reset, delete, or clean up feature work.

## Done

For every terminal sprint status (`done`, `failed`, or `blocked`), write `<sprint-directory>/03-sprint-recap.md` through Obsidian MCP. Include the sprint ID, workspace, final status, every item ID/feature ID/status/compact outcome, blocked items and upstream reasons, compact lane/batch results, integration status with `<sprint-directory>/02-integration-report.md`, and referenced feature State.md paths. On `done`, print the same concise recap. State that feature branches remain under the user's control for commit, merge, cleanup, and branch management; never claim a passing integration gate for a non-`done` sprint.
