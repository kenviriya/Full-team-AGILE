---
name: feature-pipeline
description: Use when the user wants to plan and deliver a software feature with a compact Agile team. Clarifies outcomes, produces a PRD, adds a UI spec only for user-facing work, implements against approved artifacts, then independently reviews the change.
license: MIT
---

# Feature pipeline

Run a feature through the smallest team that can deliver it.

1. **Clarify the outcome.** Ask only questions that change scope, acceptance criteria, or safety constraints. For a clear request, state the assumptions and proceed.
2. **Detect optional capabilities.** Inspect the active skill and tool inventory. When Context Mode is available, use its context-preserving gather, search, and processing tools for broad repository exploration or long command output. Otherwise, use normal repository tools. When `design-taste-frontend` is available, prefer it for user-facing design work; `design-taste-frontend-v1` is a compatible fallback.
3. **Product.** Delegate to `agile-product-manager` for a concise PRD with acceptance criteria.
4. **UX only when needed.** If the PRD has a user-facing surface, delegate to `agile-ux` for a UI spec and use the available Taste Skill to guide the design and implementation. Do not create UI work or invoke Taste Skill for backend-only changes.
5. **Implement.** Give the approved PRD and any UI spec to `agile-implementer`. The implementer should reuse existing patterns and make the smallest complete change.
6. **Review.** Delegate the completed diff and source artifacts to `agile-reviewer`. Resolve confirmed findings before calling the work done.

## Boundaries

- Context Mode and Taste Skill are optional: never attempt to invoke a capability that is absent from the active session.
- Context Mode supports exploration and analysis; it does not replace product, UX, implementation, or review ownership.
- Taste Skill guides only user-facing design work; `agile-ux` still owns the UI specification.
- Do not start implementation while requirements that materially affect behavior are unknown.
- A PRD is not a UI specification; request UX only when the feature changes an interface.
- A review reports problems; it does not silently edit the implementation.
- Keep artifacts concise and scoped to the feature. Avoid process documents for trivial changes.
