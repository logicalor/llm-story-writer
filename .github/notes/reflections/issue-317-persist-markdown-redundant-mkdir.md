---
date: "2026-05-03"
issue: 317
pr: 329
category: instruction
targets:
  - ".github/notes/gotchas.md"
  - "src/tools/_persist.py"
severity: minor
status: active
---

## `persist_markdown` calls `mkdir` redundantly — violates gotcha #047; gotcha #047 had wrong file reference

### Finding

PR #329 (issue #317) introduced `persist_markdown` in `src/tools/_persist.py`. The implementation
calls `target_path.parent.mkdir(parents=True, exist_ok=True)` immediately before calling
`_atomic_write(target_path, body)`. Since `_atomic_write` (defined in `src/tools/_io.py`) already
calls `path.parent.mkdir(parents=True, exist_ok=True)` as its first step, the explicit `mkdir`
in `persist_markdown` is redundant — a direct violation of gotcha #047.

Additionally, the text of gotcha #047 itself contained an incorrect file reference. It stated that
`_atomic_write` lives in `src/presentation/orchestrator.py`, but the canonical definition is in
`src/tools/_io.py`. `orchestrator.py` imports `_atomic_write` from `tools._io` — it is a caller,
not the definition site.

### Observation

The gotcha #047 file-location error is a plausible source of confusion: a developer reading the
gotcha and searching `orchestrator.py` for `_atomic_write` would find only import/call sites, not
the function body, and might conclude the gotcha is wrong rather than that the file reference is
wrong. This undermines trust in the gotcha and could cause the convention to be silently abandoned.

The redundant `mkdir` in `persist_markdown` is harmless (both calls use `exist_ok=True`) but:
- Creates the false impression that callers are responsible for ensuring the directory exists before
  calling `_atomic_write`
- Establishes a bad pattern for future persist helpers written alongside `persist_markdown`
- Contradicts the convention established and documented in PR #328 just one PR earlier

### Suggested Improvement

1. **Applied immediately**: Correct the file reference in gotcha #047 from
   `src/presentation/orchestrator.py` to `src/tools/_io.py`.

2. **Code fix needed** (follow-up PR): Remove the redundant `mkdir` call from `persist_markdown`
   in `src/tools/_persist.py`:
   ```python
   # Remove this line:
   target_path.parent.mkdir(parents=True, exist_ok=True)
   ```
   `_atomic_write` owns directory creation. Callers must not duplicate it.

### Action Taken

Applied: corrected `src/presentation/orchestrator.py` → `src/tools/_io.py` in gotcha #047 text.
Code fix (remove redundant mkdir from `persist_markdown`) deferred to a follow-up PR — production
code changes are outside the Reflection agent's edit scope.
