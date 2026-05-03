---
date: "2026-05-03"
issue: 323
pr: 335
category: instruction
targets:
  - ".github/agents/_shared/review-checklist.md"
severity: minor
---

## Hardcoded Savepoint Checkpoint List Can Drift After Phase Changes

### Finding

`test_resume_granularity.py` contains `_savepoint_names()` which returns a hardcoded list
of savepoint checkpoint names produced by the pipeline. If the orchestrator adds or removes
pipeline phases (which happened in issues #318 and #320), this list silently becomes stale.
Tests would then construct `PipelineState` objects with the wrong `savepoints` list,
potentially masking bugs where the resume logic misidentifies completed phases.

### Observation

This is the same class of problem as "Pipeline LLM call multiplier — timeout budget"
(issue #296): test metadata about pipeline structure that drifts without any lint, type-
check, or test failure. The review-checklist Phase 5 is the natural place to add a check
for this. Future reviewers adding new pipeline phases should be prompted to grep
`tests/integration/` for hardcoded checkpoint name lists and verify they are updated.

### Suggested Improvement

Add a "**Integration test checkpoint manifest drift**" bullet to Phase 5 of
`review-checklist.md` after the "Pipeline LLM call multiplier" bullet.

### Action Taken

Applied: Added "**Integration test checkpoint manifest drift:**" bullet to
`.github/agents/_shared/review-checklist.md` Phase 5.
