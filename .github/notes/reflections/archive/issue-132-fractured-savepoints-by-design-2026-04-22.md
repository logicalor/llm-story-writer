---
date: "2026-04-22"
issue: 132
pr: 136
category: agent
targets:
  - "src/tools/critique_runner.py"
severity: minor
status: archived
---

## Fractured savepoints in `cmd_run_arc_analysis` — intentional checkpoint resilience

### Finding

During PR #136 review, a finding noted that `cmd_run_arc_analysis` writes savepoints
incrementally — after each individual LLM call (arc_distribution → arc_promise_payoff →
arc_assessment). If the second or third LLM call fails, earlier savepoints are written but
the final `_success()` output is never emitted, leaving partial state on disk.

This was classified as a design concern ("fractured savepoints") in at least one review
finding.

### Observation

The pattern is intentional and matches the `cmd_run_critics` implementation, which also
writes per-critic savepoints as results arrive. The design is checkpoint resilience:
if an LLM call fails partway through a multi-call operation, the completed steps are
preserved on disk. On manual retry, the caller can resume from the last valid checkpoint
rather than rerunning all steps from the beginning. This is the same rationale articulated
for `run-critics`.

There is no bug. The review finding is a false positive (or a deliberate design tradeoff
acknowledgement, not a defect).

### Suggested Improvement

No improvement needed for production code. Document in this note for future reviewer
context: sequential savepoints across multiple LLM calls within a single operation is
the established resilience pattern in this codebase. A reviewer flagging "fractured
savepoints" in a multi-LLM-call operation should check whether `cmd_run_critics` uses
the same pattern before raising a Critical or Warning finding.

A gotcha entry for this pattern would be appropriate if the false-positive recurs across
multiple review cycles.

### Action Taken

No action taken — by design. Note recorded for reviewer context.
