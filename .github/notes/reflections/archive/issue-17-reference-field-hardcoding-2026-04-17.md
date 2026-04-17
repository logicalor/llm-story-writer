---
date: "2026-04-15"
issue: 17
pr: 61
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: active
---

## Stale-claim finding message hardcoded wrong field name

### Finding

During issue #17 (Build wiki-lint Tool), the stale-claim check's finding message hardcoded "first_appearance" as the source field, even when the `page_chapter` value was actually sourced from the `last_updated` YAML field. Two of 3 review models caught this. The fix introduced a `reference_field` variable that tracks which field actually provided the chapter reference.

### Observation

This is another instance of the wiring bug / semantic correctness gap documented in the issue #10 reflection. The Coder correctly implemented the logic to check multiple YAML fields (`first_appearance`, `last_updated`) but hardcoded the diagnostic message to always reference `first_appearance`. The data flow from field detection to message composition was broken — the detection logic was correct, but the message didn't reflect which path was taken.

This follows the same pattern as:
- Issue #10: `cmd_refine()` accepted `--feedback` but never passed it to the LLM
- Issue #15: Cache populated but never read by its consumer
- Issue #17: Field source detected correctly but message hardcoded to wrong field

The proposed semantic verification rule (issue #10, pending approval) would catch this — tracing the data flow from field detection to message composition would reveal the hardcoded string.

### Suggested Improvement

No new rule needed — this is additional supporting evidence for the pending issue #10 semantic verification rule proposal. The fix was applied during the review cycle.

### Action Taken

Recorded as supporting evidence for the pending issue-10 semantic verification rule proposal. No agent changes needed — the review system caught and fixed this in the current PR.
