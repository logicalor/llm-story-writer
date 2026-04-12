# Project Notes

This directory is a shared knowledge base maintained by the agent system. It captures concepts, architectural decisions, domain knowledge, and discovered gotchas that inform future development work.

## Who writes here

| Agent         | Access                                                                           |
| ------------- | -------------------------------------------------------------------------------- |
| Orchestrator  | Writes notes directly for workflow-level patterns, decisions, and deferred ideas |
| Planner       | Writes notes directly for codebase research findings during planning             |
| Contemplation | Writes notes directly for insights from project reflection                       |
| Reflection    | Writes to .github/notes/reflections/ for agent system improvements               |
| Documenter    | Writes notes directly when documentation reveals patterns worth recording        |
| Auditor       | Writes to .github/notes/audits/ for healthcheck and compliance audit reports     |

## Who reads here

All agents should check relevant notes before starting any task. Agents have direct file read access.

## File structure

Create one file per topic. Use clear, descriptive names.

| File                | Purpose                                                                                |
| ------------------- | -------------------------------------------------------------------------------------- |
| `architecture.md`   | High-level structural decisions — layer responsibilities, module boundaries, data flow |
| `domain.md`         | Business logic and domain concepts specific to this project                        |
| `patterns.md`       | Reusable implementation patterns discovered during development                         |
| `gotchas.md`        | Non-obvious behaviours, known footguns, and things that have caused bugs before        |
| `deferred.md`       | Ideas and improvements that came up but were intentionally not implemented yet         |
| `[feature-name].md` | Notes scoped to a specific feature when general files are not appropriate              |
| `reflections/`      | Agent system improvement notes — see below                                             |
| `audits/`           | Healthcheck and compliance audit reports — see below                                   |

## Reflections subdirectory

The `reflections/` subdirectory is managed by the Reflection agent and contains notes about improving the agent system itself:

| File                     | Purpose                                                |
| ------------------------ | ------------------------------------------------------ |
| `reflections/README.md`  | Guidance for the reflections directory                 |
| `reflections/issue-N.md` | Improvement notes scoped to a specific task            |
| `reflections/general.md` | Cross-cutting improvements not tied to a specific task |
| `reflections/archive/`   | Processed notes that have been applied or resolved     |

See `.github/notes/reflections/README.md` for full details on the reflection workflow.

## Audits subdirectory

The `audits/` subdirectory is managed by the Auditor agent and contains timestamped audit reports:

| File                   | Purpose                                                      |
| ---------------------- | ------------------------------------------------------------ |
| `audits/YYYY-MM-DD.md` | Audit report for the given date — findings and health rating |

## Format

Each note entry should include:

```markdown
## [Short title]

**Date:** YYYY-MM-DD
**Source:** [agent name] — issue #N / PR #N (if applicable)

[Content — as brief or as detailed as needed]
```

Notes are append-only by default. Update an existing entry only to correct it; use a new entry to add new information.

---

## Retention Policy

To keep the notes directory manageable, apply the following retention rules during periodic maintenance (e.g., at the start of a sprint or after a major release):

### Reflections (`reflections/`)

- **Active reflections** (`reflections/issue-N.md`, `reflections/general.md`): Move to `reflections/archive/` once the improvements have been applied and verified — typically after the next sprint completes.
- **Archived reflections** (`reflections/archive/`): Retain for 2 sprints (~4 weeks) after archiving, then prune. One-line stub files with no actionable content can be pruned immediately.
- `reflections/general.md` should be periodically summarised — extract applied learnings into ChromaDB conventions, then truncate the file to only active/unapplied items.

### Reviews (`reviews/`)

- Keep individual synthesis reports for the duration of their associated PR lifecycle.
- After the PR is merged, reviews may be summarised into a quarterly digest (`reviews/YYYY-QN-digest.md`) and the individual files pruned.
- Quarterly digests are retained indefinitely.

### Audits (`audits/`)

- Audit reports are retained for **1 year** from their creation date.
- After 1 year, prune reports older than 12 months, keeping the most recent 4 audits regardless of age.
- Findings that become standing conventions should be embedded into ChromaDB before pruning.

### General Notes

- Topic files (`architecture.md`, `patterns.md`, `gotchas.md`, etc.) are not pruned — they are updated in place.
- The `deferred.md` file should be reviewed each sprint; items that have shipped should be removed.
- `repo.md` is a special file referenced by agents — never prune; update in place only.
- `sprints/` notes are retained for the duration of the sprint; prune when the sprint closes.
- Ad-hoc task files (e.g. `task-N.md`) may be pruned once the task is complete and any learnings have been recorded in the relevant topic file or ChromaDB.
- Log files (e.g. `subagent-audit.log`) are transient; prune at will once reviewed.
- When a feature- or integration-specific note file becomes permanently obsolete (removed feature, deleted integration), add an `⚠️ Archived` header to the file itself **and** check this README for any table entries or retention directives that reference it — remove or update them at the same time.

