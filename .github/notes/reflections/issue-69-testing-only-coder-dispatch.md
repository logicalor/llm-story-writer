---
date: "2026-04-16"
issue: 69
pr: 71
category: agent
targets:
  - ".github/agents/orchestrator-v3.agent.md"
severity: minor
status: active
---

## Coder handles testing-only issue without separate Test Writer dispatch — positive signal

### Finding

During issue #69 (Add behavioral tests for compaction plugin), the Orchestrator dispatched the Coder to handle both the test infrastructure setup (package.json, tsconfig.json, vitest.config.ts) and the test writing (26 unit tests, 4 integration tests, 30 total). All 30 tests passed on first run. No separate Test Writer dispatch was needed.

### Observation

This is a nuance to the issue #8 reflection (Coder writes tests that should be Test Writer's responsibility). In issue #8, the Coder spontaneously wrote verification tests alongside implementation, bypassing the Test Writer's specialised workflow. Here, the entire issue was test-only — there was no production code implementation to separate from test writing. The Coder was the correct agent to dispatch because:

1. The issue required creating new test infrastructure (Node.js toolchain for a Python-only project) — this is closer to implementation than pure test writing
2. Named exports had to be added to the production plugin file to make functions testable — a code change the Test Writer shouldn't make
3. The test scenarios were tightly coupled to the implementation details of the pure functions being tested

This suggests the pending issue #8 proposal (Coder Rule: "Do not write verification tests") needs a carve-out for testing-only issues where the Orchestrator explicitly dispatches the Coder for test work. The rule should prevent spontaneous test writing during implementation, not block the Coder from being dispatched for dedicated testing tasks.

### Suggested Improvement

If/when the issue #8 proposed rule is applied, include a carve-out:

```markdown
N. **Do not write verification tests** unless explicitly dispatched for a testing-only task. If you identify test scenarios during a regular implementation dispatch, note them in your handoff summary for the Test Writer. The Orchestrator will dispatch the Test Writer separately. You may create minimal throwaway test scripts for debugging during implementation, but delete them before handoff (per Rule 7).
```

The key addition is "unless explicitly dispatched for a testing-only task" — allowing the Orchestrator flexibility to use the Coder for test-centric issues that also require infrastructure or production code changes.

### Action Taken

No action needed — positive signal recorded. Amends the pending issue #8 proposal with a carve-out clause.
