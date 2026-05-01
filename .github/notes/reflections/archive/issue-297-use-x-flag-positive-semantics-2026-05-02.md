---
date: "2026-05-02"
issue: 297
pr: 309
category: instruction
targets:
  - ".github/notes/gotchas.md"
severity: minor
---

## `use_X=True` flag semantics: True means "run X", False means "skip X"

### Finding

During issue #297 (PR #309, RecapWriterAgent), the pipeline flag
`use_improved_recap_sanitizer` was non-obvious to interpret from its name alone. The
word "improved" modifies the sanitizer noun, not the gate direction — making the polarity
ambiguous. The correct semantics: `True` = run the sanitizer; `False` = skip it.

### Observation

This positive-gate convention (`use_X=True` → activate, `use_X=False` → skip) is used
throughout the pipeline configuration flags in this codebase. It is not universally obvious,
especially when the flag name includes a modifier word ("improved") that can read as the
subject rather than the feature being gated. Agents implementing new stages or reading
existing configuration must not invert the polarity.

A second flag in the same PR (`use_multi_stage_recap_sanitizer`) follows the same
convention. Both flags default to `True` (feature on by default), which is the idiomatic
direction for `use_X` names.

### Suggested Improvement

Add a gotcha entry (gotcha #041) to `.github/notes/gotchas.md` documenting the positive-gate
convention for `use_X` pipeline flags and the pitfall of name modifiers obscuring polarity.

### Action Taken

Applied:
- Added gotcha #041 (`use_X=True` flag positive-gate semantics) to `.github/notes/gotchas.md`.
