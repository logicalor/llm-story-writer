---
date: "2026-04-16"
issue: 77
pr: 82
category: agent
targets:
  - ".github/agents/test-writer.agent.md"
  - ".github/agents/documenter.agent.md"
severity: minor
status: archived
---

## Test Writer x2 and Documenter returned empty — Coder covered

### Finding

Issue #77 (Complete ADR 003 ChromaDB migration) had Test Writer dispatched twice for test writing tasks. Both times it returned empty responses ("Agent error" with no output). The Coder agent ultimately wrote the tests. Additionally, Documenter returned empty, so documentation changes were made by Coder instead.

### Observation

This mirrors the empty response pattern documented in dispatch-retry.md and issue #78. Two distinct subagents (Test Writer and Documenter) both failed to respond. The Coder was repurposed to cover both test and documentation work.

Secondary effect: Test Writer created test files that polluted the test suite — `sys.modules` mocking at import time caused 16 test failures in unrelated tests. These polluted test files had to be deleted. This is a new variant of the test pollution pattern (issue #14, #18) specific to the Test Writer's sys.modules mocking behaviour.

### Suggested Improvement

**Test Writer test pollution:** Add a directive to test-writer.agent.md to never mock `sys.modules` at import time — mocking should be done inside test functions using `unittest.mock.patch` or via pytest fixtures, never as a module-level side effect.

**Documenter empty:** No dispatch-retry change needed — Documenter followed the protocol correctly but the model returned empty. This is a model-level failure, not an agent design gap.

### Action Taken

Applied: Added `sys.modules` import-time mocking prohibition to test-writer.agent.md. Documenter pattern noted but no change to dispatch-retry.md (already handles empty correctly).
