---
date: "2026-04-14"
issue: 12
pr: 48
category: agent
targets:
  - ".github/agents/coder.agent.md"
  - ".github/agents/orchestrator-v3.agent.md"
severity: minor
status: archived
---

## Eighth tool implementation — clean pattern adherence, stale count recurrence

### Finding

Issue #12 (Build scene-writer Tool) was the eighth tool implementation: 4 operations (parse-definitions, generate, revise, assemble-chapter), with multi-scene assembly and definitions-driven generation. Positive signals:

1. **Implementation followed outline-generator pattern well.** Clean copy-and-adapt approach. Path validation, savepoint usage, error handling to stderr, JSON output — all applied on first pass.

2. **Synthesized Review found no critical issues.** Three warnings (all fixable), one suggestion. Model agreement score 9/10 — highest consistency yet for a tool review.

3. **All fixes applied cleanly in one dispatch.** 136 tests pass, lint clean. No regression from review fixes.

4. **Stale prompt count recurrence.** `docs/tools.md` said "131 prompt templates" when the correct count was 132 (U-W-03). This is the fifth occurrence of the stale-docs pattern (issues #4, #5, #11, #30, #12). Rule 6 already covers this explicitly: "when adding or removing an item from a set that may be counted or inventoried in documentation, grep for the old count." The Coder is not consistently running this check.

5. **Pre-existing mypy issues with `sys.path`-based imports.** Systemic issue across all tools in `src/tools/` — `sys.path.insert(0, ...)` prevents mypy from resolving imports. Not an agent system issue; needs a structural fix (e.g., proper packaging or mypy path configuration).

### Observation

The tool implementation pipeline continues to mature. Pattern carry-forward for security (Rule 9) and structural patterns is reliable. The remaining recurring issues — dead code (Rule 7) and stale counts (Rule 6) — are _compliance gaps_ rather than rule gaps. The rules exist and are clear; they're just not consistently executed.

This suggests the value of the pending semantic verification rule (issue #10) is high: it forces the Coder to trace through each operation systematically, which would naturally surface both dead code and count mismatches as side effects of a thorough pre-handoff review.

### Suggested Improvement

No agent/skill/instruction changes needed. Positive signals and recurring patterns recorded.

### Action Taken

No action needed — positive signal recorded.
