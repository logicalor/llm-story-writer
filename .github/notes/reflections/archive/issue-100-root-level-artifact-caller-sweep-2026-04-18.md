---
date: "2026-04-18"
issue: 100
pr: 102
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## Root-level artifact files missed in constructor-parameter removal sweep

### Finding

During issue #100 (PR #102, remove dead `rag_service` parameter from the outline strategy stack),
the Coder's grep sweep was thorough for files inside `src/` but missed three root-level artifacts
that still called the constructor with the removed parameter:

- `test_rag_integration.py` — integration smoke test at the project root
- `demo_rag_integration.py` — demonstration script at the project root
- `RAG_PROMPT_FILENAME_INTEGRATION.md` — documentation referencing the removed argument

The GPT reviewer caught all three. The task completed correctly, but only because of the
synthesized review — the Coder's self-verification sweep was insufficient.

### Observation

Coder Rule 6 already requires a workspace-wide grep after text sweeps. However, in practice the
Coder scoped the grep to `src/` — a natural but incorrect boundary, since the modified classes
lived in `src/`. Root-level Python scripts (`test_*.py`, `demo_*.py`, `migrate_*.py`) are
callers of `src/` APIs and exist outside `src/`. They do not appear in a search scoped to the
source directory.

This is a distinct pattern from the existing Rule 6 sub-bullets (package removal stale docs,
provider variant prose). Package-removal sub-bullets target *documentation* about removed
capabilities. This is about *code callers* of a changed API — callers that exist outside the
modified file tree. The "workspace-wide" language in Rule 6 is correct but ambiguous enough that
`src/` feels like "the workspace" for source-level tasks.

### Suggested Improvement

Add a sub-bullet to Coder Rule 6:

> **When removing or renaming a constructor parameter, method argument, or class attribute**
> — grep the entire workspace (not just `src/`) for callers using the removed name as a keyword
> argument, or for any instantiation of the class. Explicitly include root-level Python scripts
> (`test_*.py`, `demo_*.py`, `migrate_*.py`) — these often call `src/` APIs directly and sit
> outside the `src/` search scope. A grep scoped to `src/` silently misses integration smoke
> tests and demonstration scripts at the project root.

### Action Taken

Applied: added sub-bullet to Coder Rule 6 in `.github/agents/coder.agent.md` covering
constructor/method parameter removal caller sweep, with explicit mention of root-level scripts.
