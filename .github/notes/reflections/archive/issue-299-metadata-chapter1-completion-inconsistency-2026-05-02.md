---
date: "2026-05-02"
issue: 299
pr: 311
category: agent
targets:
  - ".github/notes/gotchas.md"
severity: minor
---

## `metadata-chapter-1` marks completion inside `try` block — inconsistent resume semantics

### Finding

`_continue_pipeline` contains three advisory metadata phases. Two of them (`metadata-outline`, `metadata-final`) call `await _mark_phase_complete(...)` unconditionally after their `try/except` block — they are always marked complete regardless of whether metadata generation succeeded. The third, `metadata-chapter-1`, calls `state.completed_phases.append("metadata-chapter-1")` and `await _write_savepoint(state)` inside the `try` block, so the phase is only marked complete on success.

Consequence: if `metadata-chapter-1` fails during a run, the savepoint does not include it in `completed_phases`. On pipeline resume, the condition `"metadata-chapter-1" not in state.completed_phases` is satisfied and the phase is retried. For `metadata-outline` and `metadata-final`, the phase is not retried even after failure.

### Observation

The behavioral difference is undocumented and not immediately obvious from reading the orchestrator. It may be intentional (chapter-1 metadata is the highest-fidelity pass since it has real chapter prose; retrying it on resume is reasonable). However, no comment or doc block explains the distinction. Future maintainers adding metadata phases will likely follow the `_mark_phase_complete` pattern (used by every other advisory phase) and accidentally create an always-complete phase when retrying-on-failure is the desired semantics.

### Suggested Improvement

Document the difference in `.github/notes/gotchas.md` as an info-level gotcha: advisory phases that use `_mark_phase_complete` are always marked complete; advisory phases that append to `completed_phases` inside the `try` block are only marked complete on success and will be retried on pipeline resume.

### Action Taken

Applied: Added gotcha #046 to `.github/notes/gotchas.md` documenting the advisory-phase completion semantics split.
