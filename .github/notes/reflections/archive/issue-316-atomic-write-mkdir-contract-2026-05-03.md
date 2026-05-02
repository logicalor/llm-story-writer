---
date: "2026-05-03"
issue: 316
pr: 328
category: instruction
targets:
  - ".github/notes/gotchas.md"
severity: minor
---

## `_atomic_write` handles `mkdir` internally — callers must not duplicate it

### Finding

During issue #316 (PR #328), `_write_savepoint` was refactored to use `_atomic_write`. The old implementation called `path.parent.mkdir(parents=True, exist_ok=True)` before writing. This line was safely removed because `_atomic_write` in `src/presentation/orchestrator.py` already calls `path.parent.mkdir(parents=True, exist_ok=True)` internally.

### Observation

This is a non-obvious contract. Without knowing the internals of `_atomic_write`, a Coder refactoring a caller might defensively preserve the `mkdir` call, leading to a redundant mkdir that obscures the actual ownership of directory creation.

Documenting this as a codebase pattern prevents:
- Redundant `mkdir` calls accumulating in callers
- Incorrect assumption that callers are responsible for ensuring the directory exists
- Confusion during future atomic write refactors about who creates the directory

### Suggested Improvement

Add an entry to `.github/notes/gotchas.md` documenting this contract (as gotcha #047).

### Action Taken

Applied: added gotcha #047 — `_atomic_write` handles `mkdir` internally — to `.github/notes/gotchas.md`.
