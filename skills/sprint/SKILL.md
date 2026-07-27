---
name: sprint
description: Coordinates a dependency-safe sprint backlog by delegating each feature-sized item to the resumable feature workflow and gating final integration.
license: MIT
---

# Sprint delivery

When invoked as `/sprint <backlog description>` or `/sprint continue <sprint-id>`:

## Coordinator boundary

1. Sprint coordinates multiple feature-sized backlog items. It does not replace `full-team-agile:feature`.
2. Every item is delivered by one separate agent invoking `full-team-agile:feature`. That feature workflow remains the sole authority for questions, PRD, UX, implementation, testing, review, cleanup, State.md artifacts, repository selection, Git branches, and worktree safeguards.
3. Sprint must not directly delegate implementation, QA, or review agents. It must not create, reset, switch, merge, delete, or clean up feature branches, worktrees, repositories, or feature artifacts.
4. Feature State.md is authoritative for each item's delivery status. Sprint records only its feature ID, State.md reference, compact observed outcome, dependencies, scheduling information, and integration evidence.

## State contract

1. Capture the invocation workspace root and use its basename as `<workspace-name>`.
2. For a new sprint, generate and immediately print a unique readable `<sprint-id>` from the backlog slug, lowercase UTC timestamp, and short random suffix. Never reuse a sprint folder. For continuation, validate the exact ID against `^[a-z0-9]+(?:-+[a-z0-9]+)*$`; reject `/`, `.`, whitespace, and all other characters.
3. Persist `Sprints/<workspace-name>/<sprint-id>/State.md` before dispatching any item. Keep `01-sprint-plan.md` and `02-integration-report.md` in the same folder.
4. State.md is authoritative for sprint coordination. Reread it before planning changes, dispatch, dependency evaluation, continuation, and the integration gate.
5. Use versioned compact state containing `sprintId`, `stage`, `workspace`, `backlog`, `items`, `lanes`, `integration`, and `history`. Each item stores its description, feature ID, feature State.md path, status, `dependsOn`, declared ownership/resources, lane, blockers, and compact outcome.
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

1. Before dispatching a ready item, assign and persist its feature ID.
2. Start one separate agent per ready item. Instruct it to invoke `full-team-agile:feature` with the scoped requirement, sprint ID, item ID, `feature-id=<assigned-feature-id>`, explicit repository scope, dependencies already satisfied, and ownership/interface constraints.
3. The delegate must follow the canonical feature workflow and use `Features/<workspace-name>/<feature-id>/State.md` as its delivery record. Sprint must not bypass its questions or write its PRD.
4. After a delegate reaches a reportable state, reread its referenced feature State.md and record the compact observed outcome in sprint state.
5. If an item is `failed` or `blocked`, do not dispatch a dependent item. Mark direct and transitive dependents `blocked` with the upstream item ID and reason. Continue independent ready lanes.
6. If a feature is waiting for user answers, retain the item's `running` status; it blocks only its dependents.
7. On continuation, retain feature IDs, refresh observed feature outcomes from their State.md files, and recompute readiness only for nonterminal items. Never recreate feature work automatically.

## Integration gate

1. When all items are terminal, set the sprint to `blocked` if any item is `failed`, `blocked`, or `skipped`. Do not claim completion or run a passing integration gate.
2. Run the integration gate only when every item is `done`.
3. Before the gate, reread every referenced feature State.md and verify each is done with passing QA and approved review evidence.
4. Collect relevant declared cross-item contract checks and recorded repository-specific checks. Run only integration checks relevant to the planned interactions and permitted without overriding feature safeguards.
5. Write commands, pass/fail evidence, impacted items, and failures to `02-integration-report.md`.
6. Mark the sprint `done` only when every required integration check passes. A failed check marks the sprint `failed`; do not automatically roll back, reopen, merge, reset, delete, or clean up feature work.

## Done

On `done`, summarize every item ID, feature ID, status, blocked items, and integration evidence. List the sprint State.md, plan, integration report, and referenced feature State.md paths. State that feature branches remain under the user's control for commit, merge, and branch management.
