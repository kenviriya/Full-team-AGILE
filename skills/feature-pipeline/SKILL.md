---
name: feature-pipeline
description: Use when the user wants to plan and deliver a software feature with a compact Agile team. Clarifies outcomes, produces a PRD, adds a UI spec only for user-facing work, implements against approved artifacts, then independently reviews the change.
license: MIT
---

# Feature pipeline

Run a feature through the smallest team that can deliver it.

1. **Clarify the outcome.** Ask only questions that change scope, acceptance criteria, or safety constraints. For a clear request, state the assumptions and proceed.
2. **Product.** Delegate to `agile-product-manager` for a concise PRD with acceptance criteria.
3. **UX only when needed.** If the PRD has a user-facing surface, delegate to `agile-ux` for a UI spec. Do not create UI work for backend-only changes.
4. **Implement.** Give the approved PRD and any UI spec to `agile-implementer`. The implementer should reuse existing patterns and make the smallest complete change.
5. **Review.** Delegate the completed diff and source artifacts to `agile-reviewer`. Resolve confirmed findings before calling the work done.

## Boundaries

- Do not start implementation while requirements that materially affect behavior are unknown.
- A PRD is not a UI specification; request UX only when the feature changes an interface.
- A review reports problems; it does not silently edit the implementation.
- Keep artifacts concise and scoped to the feature. Avoid process documents for trivial changes.
