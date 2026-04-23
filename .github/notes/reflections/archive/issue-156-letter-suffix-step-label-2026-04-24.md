---
date: "2026-04-24"
issue: 156
pr: 157
category: instruction
targets:
  - ".github/agents/_shared/review-checklist.md"
severity: minor
status: archived
---

## Letter-suffix step labels (2a., 2b.) not covered by numbered-step-continuity check

### Finding

The new "load approved outline" step in `chapter-outline-expander.md` was added as step "2a." — a letter-suffix convention not used by any other agent workflow. All three reviewers flagged it unanimously. The existing "Numbered step continuity" checklist item covers gaps (1, 2, 8) but does not explicitly mention letter-suffix labels as a disallowed variant.

### Observation

Letter-suffix step labels (`2a.`, `2b.`) create parsing ambiguity risks identical to gaps: LLMs reading the source may treat "2a." as a sub-bullet of step 2, skip it when resuming at "step 3", or miscount the total step length. The existing checklist item was written with numeric gaps in mind (from issue #144, PR #145); the `2a.` issue is the variant where a new step is inserted but receives a hybrid label instead of a proper integer.

The fix is straightforward: either promote the new step to the next integer (3, shifting later steps) or demote it to an indented sub-bullet if it is genuinely inseparable from its parent step. The "2a." notation should be treated as a disallowed shorthand.

### Suggested Improvement

Extend the existing "Numbered step continuity" checklist item to explicitly prohibit letter-suffix labels, citing this issue as the source.

### Action Taken

Applied: extended the "Numbered step continuity" item in `.github/agents/_shared/review-checklist.md` to include a sentence prohibiting letter-suffix labels (e.g. `2a.`).
