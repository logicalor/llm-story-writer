---
date: "2026-04-25"
issue: 161
pr: 171
category: instruction
targets:
  - ".github/notes/gotchas.md"
  - ".github/agents/_shared/review-checklist.md"
severity: minor
status: archived
---

## Use `isinstance()` for type dispatch — never `type(x).__name__` string comparison

### Finding

PR #171's `_continue_pipeline()` in `src/presentation/orchestrator.py` detected batch mode using:

```python
batch_mode = type(gate).__name__ == "NullApprovalGate"
```

Two of three models (Claude and Gemini) independently flagged this as a fragile anti-pattern
(M-W-01 Warning). `type(x).__name__` returns the class's literal name string; this comparison
breaks silently if `NullApprovalGate` is subclassed (the subclass has a different `__name__`) or
if the class is renamed. `isinstance()` is the semantically correct expression of the same intent
and survives both scenarios.

GPT did not flag this finding.

### Observation

`type(x).__name__` string comparison is a common shortcut that passes code review inattentively.
It produces no lint warning, no type error, and no runtime error — it simply returns `False`
silently in the subclass case. For gate/mode detection patterns (where the class *is* the
discriminant), the pattern is especially risky because behavior changes invisibly when a caller
substitutes a subclass. Making this an explicit review checklist item increases catch rate.

### Suggested Improvement

1. Add a Phase 2 General bullet to `.github/agents/_shared/review-checklist.md` flagging
   `type(x).__name__` comparisons.
2. Add gotcha entry #019 to `.github/notes/gotchas.md` under a new `## Python Patterns`
   section documenting the `isinstance()` requirement.

### Action Taken

Applied:
- Added gotcha entry #019 (`gotcha-isinstance-not-type-name-019`) to `.github/notes/gotchas.md`
  under `## Python Patterns`.
- Added a Phase 2 General bullet to `.github/agents/_shared/review-checklist.md`.
