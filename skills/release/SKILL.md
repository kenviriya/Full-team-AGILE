---
name: release
description: Safely releases a completed sprint by default, or an explicitly selected completed feature, through durable preflight, confirmation, validation, tagging, and push.
license: MIT
---

# Release delivery

When invoked as `/release <sprint-id> version=<major.minor.patch> target=<branch> remote=<remote>`, `/release feature <feature-id> version=<major.minor.patch> target=<branch> remote=<remote> repositories=<paths|all>`, or `/release continue <release-id>`:

## Release boundary

1. Release is the only workflow that performs release Git mutations. `full-team-agile:feature` remains authoritative for feature delivery, and `full-team-agile:sprint` remains authoritative for coordination and integration.
2. A bare release target is a sprint ID. Do not reinterpret an invalid or missing sprint as a feature release.
3. Feature release is explicit: require the `feature <feature-id>` form.
4. Release never asks feature or sprint lifecycle agents to redo product definition, UX, implementation, QA, review, cleanup, repository selection, or integration.
5. Release must not stage arbitrary work, stash, reset, force-push, delete branches or tags, automatically roll back, or automatically publish to an external registry or release service.

## Inputs and eligibility

1. Require `version=<major.minor.patch>` matching `^[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$`. Use the exact release tag `v<version>`.
2. Require a non-empty `target=<branch>` every time. Never infer `main`, a default branch, or another target.
3. Require a non-empty `remote=<remote>` every time a push is planned. Never infer an upstream remote.
4. For a multi-repository release, require explicit workspace-relative `repositories=<path,...>` or `repositories=all`. Never infer all repositories. A single-repository target may use its recorded repository only after it is shown in the preflight plan.
5. A sprint release requires the sprint's exact recorded State.md reference to be `done`, passing evidence in its `02-integration-report.md`, and every exact referenced feature State.md to be done with passing QA and approved review evidence.
6. A feature release requires its exact recorded Feature State.md reference to be done with passing QA and approved review evidence.
7. Reject missing, stale, outside-workspace, unselected, or ambiguous repositories. Do not release a repository merely because a feature or sprint once mentioned it.
8. Reject an existing local or remote `v<version>` tag, a conflicting release ID, or a release target whose recorded source branch cannot be verified.

## State contract

1. Capture the invocation workspace root and use its basename as `<workspace-name>`. Durable release artifacts use Obsidian MCP vault tools only, never project-relative filesystem operations. The resolved release directory is `<artifact-root>/Releases/<workspace-name>/<release-id>/` (omit the prefix and slash when `artifact_root` is empty); `<artifact-root>` is the validated vault-relative parent announced at session start.
2. For a new release, generate and immediately print a unique readable `<release-id>` from the target kind, version slug, lowercase UTC timestamp, and short random suffix. Never reuse a release folder. For continuation, validate the exact ID against `^[a-z0-9]+(?:-+[a-z0-9]+)*$`; reject `/`, `.`, whitespace, and all other characters.
3. Persist `<artifact-root>/Releases/<workspace-name>/<release-id>/State.md` through Obsidian MCP before preflight or mutation. Keep `01-release-plan.md`, `02-release-validation.md`, and `03-release-recap.md` in the same vault directory.
4. State.md is authoritative for release execution. Reread it through Obsidian MCP before preflight, confirmation, every repository mutation, push, publishing, continuation, and recap. On continuation, look first at the configured path, then at legacy `Releases/<workspace-name>/<release-id>/State.md` only when the configured root is nonempty; stop if both exist. A missing `artifactRoot` means `""`; once found, its recorded artifact root and exact State.md path are authoritative. Never relocate artifacts.
5. Use versioned compact state containing `releaseId`, `artifactRoot`, `mode`, `targetReference`, `version`, `target`, `remote`, `repositories`, `stage`, `confirmation`, `validation`, `push`, `publishing`, and `history`.
6. Per repository, record only the workspace-relative path, recorded source branch and SHA, target branch and preflight SHA, release branch, merge order/results, validated release SHA, tag state, target-update state, push state, and compact failures. Never copy PRDs, UI specs, review notes, credentials, headers, tokens, raw publish transcripts, or arbitrary Git output into release state.

## Preflight and confirmation

1. Resolve every selected repository to its canonical Git root and reread the target feature or sprint state before any Git action.
2. Verify the recorded source branch exists at its recorded SHA, feature work is committed, target exists, target SHA is captured, local trees are clean, no selected branch is occupied by another worktree, and no `v<version>` tag exists locally or on the named remote.
3. Derive merge order from sprint dependency order. A feature release has one source branch per selected repository. Do not invent ordering for unspecified cross-repository dependencies.
4. Determine only relevant recorded validation commands and cross-item integration checks. Record them in `01-release-plan.md` before mutation.
5. Persist a frozen preflight plan naming each repository, source and target branches with SHAs, release branch, merge order, version/tag, validation commands, named remote, planned target update, and planned push.
6. Request one fresh confirmation after preflight and before the first mutation. The confirmation must name the selected repositories, source and target branches and SHAs, `release/<release-id>` branches, merge order, `v<version>` tag, validation commands, remote, and push action.
7. A prior confirmation, feature approval, sprint approval, or continuation request is not release confirmation. If confirmation is denied, leave the release in a non-mutating awaiting-confirmation state.

## Local release sequence

1. After fresh confirmation, create `release/<release-id>` from the validated target SHA in each selected repository. Do not reuse an existing release branch.
2. Merge the recorded committed source branch into that release branch with `--no-ff`, in the recorded dependency order. Stop that repository on a conflict or failed merge; never auto-resolve, reset, or roll back.
3. Run the frozen release validation commands after merges. Write commands, compact pass/fail evidence, and affected repositories to `02-release-validation.md`.
4. Only after every required validation passes, create an annotated `v<version>` tag at the validated release commit in each selected repository.
5. Before advancing a target branch, reverify that it still equals its captured preflight SHA. Advance it only by the validated release commit; if it moved, stop without force-updating it.
6. Record every completed repository step immediately. A failure in one repository does not authorize rollback or destructive work in another repository.

## Push and optional publishing

1. After local release success and the same fresh confirmation, push each updated target branch and its exact annotated `v<version>` tag to the explicitly named remote. Do not force-push and do not push unplanned refs.
2. Record push result per repository. If a push fails after another repository succeeds, keep completed records and mark only incomplete work failed or pending; do not remerge, retag, or repush a recorded success on continuation.
3. External publication is disabled by default. Run it only when the request supplies a repository-qualified release command or policy and the user separately confirms that exact external action.
4. Never store credentials, authorization headers, registry tokens, request bodies, or raw publish transcripts in release state, artifacts, normal status output, or error messages.

## Continuation and recap

1. On `/release continue <release-id>`, reread State.md and revalidate recorded roots, source SHAs, target SHAs, release branches, tags, validation state, and push state before resuming only the incomplete step.
2. Do not recreate a completed merge, tag, target update, push, or external publication. If revalidation finds an unexpected ref change, stop and require a new preflight and confirmation rather than guessing.
3. For every terminal release status (`done`, `failed`, or `blocked`), write `03-release-recap.md` with release ID, target reference, version, final status, each selected repository and compact outcome, validation reference, tag/target/push status, incomplete work, and safe next action.
4. On `done`, print the same concise recap. State that external publishing occurred only when separately confirmed, and that release branches and any remaining feature branches stay under the user's control for cleanup and branch management.
