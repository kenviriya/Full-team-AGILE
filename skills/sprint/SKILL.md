---
name: sprint
description: Coordinates a dependency-safe sprint backlog by delegating each feature-sized item to the resumable feature workflow and gating final integration.
license: MIT
---

# Sprint delivery

When invoked as `/sprint <backlog description>` or `/sprint continue <sprint-id>`:

## Coordinator boundary

1. Sprint coordinates multiple feature-sized backlog items. It does not replace `full-team-agile:feature`.
2. Every selected item is delivered by one separate agent invoking `full-team-agile:feature`. That feature workflow remains the sole authority for questions, PRD, UX, implementation, testing, review, cleanup, State.md artifacts, repository selection, Git branches, and worktree safeguards.
3. Each delegated feature workflow routes its own product-manager, conditional UX, backend/frontend implementation, QA, and code-review agents. Sprint must not directly delegate those lifecycle agents.
4. Sprint must not create, reset, switch, merge, delete, or clean up feature branches, worktrees, repositories, or feature artifacts. A `done` sprint may be released only through the explicit `full-team-agile:release` workflow.
5. Feature State.md is authoritative for each item's delivery status. Sprint records only its feature ID, State.md reference, compact observed outcome, dependencies, scheduling information, and integration evidence.

## State contract

1. Capture the invocation workspace root and use its basename as `<workspace-name>`. Durable sprint artifacts use Obsidian MCP vault tools only, never project-relative filesystem operations. The resolved sprint directory is `<artifact-root>/Sprints/<workspace-name>/<sprint-id>/` (omit the prefix and slash when `artifact_root` is empty); `<artifact-root>` is the validated vault-relative parent announced at session start.
2. For a new sprint, generate and immediately print a unique readable `<sprint-id>` from the backlog slug, lowercase UTC timestamp, and short random suffix. Never reuse a sprint folder. For continuation, validate the exact ID against `^[a-z0-9]+(?:-+[a-z0-9]+)*$`; reject `/`, `.`, whitespace, and all other characters.
3. Persist `<artifact-root>/Sprints/<workspace-name>/<sprint-id>/State.md` through Obsidian MCP before dispatching any item. Keep `01-sprint-plan.md`, `02-integration-report.md`, and `03-sprint-recap.md` in the same vault directory.
4. State.md is authoritative for sprint coordination. Reread it through Obsidian MCP before planning changes, dispatch, dependency evaluation, continuation, and the integration gate. On continuation, look first at the configured path, then at legacy `Sprints/<workspace-name>/<sprint-id>/State.md` only when the configured root is nonempty; stop if both exist. A missing `artifactRoot` means `""`; once found, its recorded artifact root and exact State.md path are authoritative. Never relocate artifacts.
5. Use versioned compact state containing `sprintId`, `artifactRoot`, `stage`, `workspace`, `backlog`, `items`, `lanes`, `integration`, and `history`. Each item stores its description, feature ID, exact feature State.md reference, status, `dependsOn`, declared ownership/resources, lane, blockers, and compact outcome.
6. Item and sprint IDs are safe path segments. Dependencies refer only to existing item IDs. Reject self-dependencies and dependency cycles before any dispatch.
7. An item status is exactly one of `planned`, `ready`, `running`, `done`, `blocked`, `failed`, or `skipped`. Record its generated feature ID exactly once before delegation.
8. Do not copy PRDs, UI specs, review notes, branch metadata, temporary-artifact registries, or repository paths from a feature folder into sprint state.

## Planning and lanes

1. Ask only questions material to feature acceptance boundaries, dependencies, repository scope, or shared ownership/resources. Do not infer an unspecified dependency or ownership claim.
2. Before dispatch, write `01-sprint-plan.md` with every item ID, feature-sized description, acceptance boundary, dependency IDs, intended repository scope when known, ownership/resources, lane, lane rationale, and planned feature invocation.
3. An item is `ready` only when every dependency is `done` and it has no unresolved planning blocker.
4. Run items concurrently only when they target different selected repositories, have disjoint declared ownership, and have no shared path area, API/shared contract, schema/migration, generated artifact, lockfile/configuration, fixture, or external test resource. The feature workflow has no separate checkout/worktree isolation for concurrent feature IDs in one repository.
5. Unknown ownership or unresolved contracts serialize work rather than allowing optimistic parallelism. Items sharing a selected repository serialize even when their declared resources are otherwise disjoint.
6. Lanes are scheduling groups, not shared implementation assignments. Launch at most one feature agent per item.

## Delegation and status

1. Before dispatching, reread State.md, compute ready items, and select one pairwise-safe dispatch batch under the lane rules.
2. Before launching the batch, assign and persist each selected item's feature ID and record its launch as pending.
3. Launch one separate feature delegate per selected ready item in a single parallel dispatch. Instruct each delegate to invoke `full-team-agile:feature` with the scoped requirement, sprint ID, item ID, `feature-id=<assigned-feature-id>`, explicit repository scope, dependencies already satisfied, and ownership/interface constraints.
4. Record each launch result. Mark an item `running` only after its delegate starts. If a delegate does not start or is denied before a feature State.md exists, retain its assigned feature ID, return it to `ready`, record the launch failure, and retry only that same feature assignment on a later dispatch.
5. The delegate must follow the canonical feature workflow and use the item's exact recorded Feature State.md reference as its delivery record. Sprint must not bypass its questions or write its PRD.
6. A dispatch batch is a scheduling snapshot: items that become ready while it runs wait for the next readiness evaluation.
7. After a delegate reaches a reportable state, reread its referenced feature State.md and record the compact observed outcome in sprint state.
8. If an item is `failed` or `blocked`, do not dispatch a dependent item. Mark direct and transitive dependents `blocked` with the upstream item ID and reason. Continue independent ready lanes.
9. If a feature is waiting for user answers, retain the item's `running` status; it blocks only its dependents.
10. On continuation, retain feature IDs, refresh observed feature outcomes from their State.md files, and recompute readiness only for nonterminal items. Never recreate feature work automatically.

## Integration gate

1. When all items are terminal, set the sprint to `blocked` if any item is `failed`, `blocked`, or `skipped`. Do not claim completion or run a passing integration gate.
2. Run the integration gate only when every item is `done`.
3. Before the gate, reread every referenced feature State.md and verify each is done with passing QA and approved review evidence.
4. Collect relevant declared cross-item contract checks and recorded repository-specific checks. Run only integration checks relevant to the planned interactions and permitted without overriding feature safeguards.
5. Write commands, pass/fail evidence, impacted items, and failures to `02-integration-report.md`.
6. Mark the sprint `done` only when every required integration check passes. A failed check marks the sprint `failed`; do not automatically roll back, reopen, merge, reset, delete, or clean up feature work.

## Done

For every terminal sprint status (`done`, `failed`, or `blocked`), write `03-sprint-recap.md`. Include the sprint ID, workspace, final status, every item ID/feature ID/status/compact outcome, blocked items and upstream reasons, compact lane/batch results, integration status with `02-integration-report.md`, and referenced feature State.md paths. On `done`, print the same concise recap. State that feature branches remain under the user's control for commit, merge, cleanup, and branch management; never claim a passing integration gate for a non-`done` sprint.
