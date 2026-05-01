# Reflections

This directory is managed by the **Reflection agent** and contains notes about improving the agent system itself — agents, skills, and instructions.

## File Naming Convention

| Pattern | Purpose |
| ------- | ------- |
| `issue-N.md` | Improvement notes from a specific task (GitHub issue #N) |
| `general.md` | Cross-cutting improvements not tied to a specific task |
| `TEMPLATE.md` | Canonical note format template |
| `archive/` | Processed notes that have been applied or resolved |

## Lifecycle

1. **Record** — During a task, the Orchestrator dispatches observations to the Reflection agent, which records them here.
2. **Collate** — At task end, the Reflection agent reads all active notes, groups by target, and classifies severity.
3. **Apply** — Minor improvements (typos, clarifications) are auto-applied (max 3 per dispatch). Major improvements (structural changes) are proposed for approval.
4. **Embed** — All new reflections are embedded into the `reflections` ChromaDB collection for semantic recall.
5. **Archive** — Processed notes are **moved** (`mv`) to `archive/` with a date suffix. The `archive/` directory is invisible to the Reflection agent — never read after archival.

## Archiving Paradigm

**Archive = location, not flag.** A note's state is determined entirely by its directory:

- `reflections/*.md` — active, pending collation
- `reflections/archive/*.md` — archived, invisible

There is **no `status:` frontmatter field**. Do not add one. The Reflection agent will not check for it. Move the file or don't.

## Severity Classification

| Severity | Criteria | Action |
| -------- | -------- | ------ |
| **minor** | Typos, clarifications, missing examples, broken links, formatting | Auto-apply |
| **major** | New handoffs, workflow steps, structural changes, new agents/skills, tool changes | Propose for approval |

## Note Format

See `TEMPLATE.md` for the canonical format.
