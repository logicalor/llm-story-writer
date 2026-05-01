---
date: "2026-05-02"
issue: 296
pr: 308
category: instruction
targets:
  - ".github/agents/_shared/review-checklist.md"
severity: minor
---

## Multi-stage pipeline LLM call multiplier not checked against integration test timeout

### Finding

PR #308 rewrote `OutlinePlannerAgent` with a 4-stage sequential pipeline (skeleton →
expand-per-chapter × N → strip → persist), replacing the previous single-call approach.
Each stage makes one LLM call, so a two-chapter story now requires at minimum 4 LLM calls
for the outline phase alone (skeleton × 1 + expand × 2 + strip × 1), compared to 1 call
previously. The integration test `test_two_chapter_story_batch` timed out during the
session — expected, as no LM Studio instance was running — but the `TIMEOUT_SECONDS`
constant (600) in `tests/integration/test_end_to_end_headless.py` carries no annotation
about the assumed call count it was sized for.

### Observation

When a pipeline stage is refactored from single-call to N-stage, the integration test
budget silently becomes tighter. A 600s budget that was sized for a small number of LLM
calls is adequate only when the per-call latency leaves sufficient headroom; with a
slow local model and a 4-stage outline phase plus subsequent per-chapter write and
edit stages, that headroom may be consumed faster than expected. Without a comment
documenting the original sizing assumption, the next multi-stage refactoring has no
baseline to compare against, and reviewers will not know whether to flag the constant
for review.

The Phase 5 Testing Review checklist already contains a "Live test skip guards" check
(added in issue #159), but has no check prompting reviewers to verify that integration
test timeout constants are still adequate after pipeline call-count changes.

### Suggested Improvement

Add a bullet to Phase 5 Testing Review in `.github/agents/_shared/review-checklist.md`
prompting reviewers to check whether the integration test `TIMEOUT_SECONDS` constant is
still adequate when a PR multiplies LLM call count per pipeline stage.

### Action Taken

Applied:
- Added `Pipeline LLM call multiplier — timeout budget` check to Phase 5 Testing Review
  in `.github/agents/_shared/review-checklist.md`, after the existing "Live test skip
  guards" bullet.
