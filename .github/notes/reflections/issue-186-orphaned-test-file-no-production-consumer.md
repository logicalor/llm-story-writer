---
date: "2026-04-26"
issue: 186
pr: 199
category: agent
targets:
  - ".github/agents/test-writer.agent.md"
severity: minor
status: active
---

## Test Writer created dedicated test file for helper with no production consumer

### Finding

During PR #199 (fix/issue-186-strengthen-e2e-test), the Test Writer added `test_generate_with_retry.py` — a dedicated test file for a `generate_with_retry` helper that had zero callers in production code (`src/`). The helper was orphaned: it existed as infrastructure but nothing in the pipeline invoked it. All three reviewers caught the file; it was deleted as part of the final PR.

### Observation

A test file written for an orphaned helper provides no regression protection — the tests can never catch a real bug because the helper is never called in production. Worse, it normalises writing tests for dead code, potentially growing the test surface against things that may eventually be removed anyway. The existing Test Writer Step 1.4 addresses *pre-existing* broken helpers when extending a file, but does not address the case where the Test Writer itself creates a new dedicated test file for a production subject that has no callers.

### Suggested Improvement

Add a Step 1 bullet to `test-writer.agent.md` requiring a production-consumer grep before creating a new dedicated test file. If the subject function/class has no callers in `src/`, it is orphaned — flag it in the verification report rather than writing tests for it.

### Action Taken

Applied: added bullet 5 to Step 1 "Research Before Writing" in `test-writer.agent.md` — requiring a `grep src/` consumer check before creating a new test file for any function or class.
