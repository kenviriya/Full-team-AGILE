# Graph Report - Full-team-AGILE  (2026-07-21)

## Corpus Check
- 12 files · ~2,974 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 48 nodes · 39 edges · 10 communities (7 shown, 3 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `2b8e8984`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- marketplace.json
- Full-team-AGILE
- Feature delivery
- backend-engineer.md
- frontend-engineer.md
- qa-engineer.md
- Install
- code-reviewer.md
- product-manager.md
- ux-designer.md

## God Nodes (most connected - your core abstractions)
1. `Full-team-AGILE` - 6 edges
2. `Feature delivery` - 6 edges
3. `Install` - 4 edges
4. `owner` - 3 edges
5. `Use` - 3 edges
6. `$schema` - 1 edges
7. `url` - 1 edges
8. `plugins` - 1 edges
9. `Codex` - 1 edges
10. `Kimi Code` - 1 edges

## Surprising Connections (you probably didn't know these)
- None detected - all connections are within the same source files.

## Import Cycles
- None detected.

## Communities (10 total, 3 thin omitted)

### Community 0 - "marketplace.json"
Cohesion: 0.25
Nodes (7): description, name, owner, name, url, plugins, $schema

### Community 1 - "Full-team-AGILE"
Cohesion: 0.25
Nodes (7): Claude Code requirements, Develop locally, Full-team-AGILE, License, Optional workflow integrations, Update, Use

### Community 2 - "Feature delivery"
Cohesion: 0.29
Nodes (6): Boundaries, Done, Feature delivery, Feature identity and state, Stages, Workspace isolation

### Community 3 - "backend-engineer.md"
Cohesion: 0.50
Nodes (3): Constraints, Final response, Process

### Community 4 - "frontend-engineer.md"
Cohesion: 0.50
Nodes (3): Constraints, Final response, Process

### Community 5 - "qa-engineer.md"
Cohesion: 0.50
Nodes (3): Constraints, Process, Response format

### Community 6 - "Install"
Cohesion: 0.50
Nodes (4): Codex, Install, Kimi Code, OpenCode

## Knowledge Gaps
- **34 isolated node(s):** `$schema`, `name`, `description`, `name`, `url` (+29 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Full-team-AGILE` connect `Full-team-AGILE` to `Install`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Why does `Install` connect `Install` to `Full-team-AGILE`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **What connects `$schema`, `name`, `description` to the rest of the system?**
  _34 weakly-connected nodes found - possible documentation gaps or missing edges._