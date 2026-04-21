---
date: "2026-04-21"
issue: 117
pr: 118
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## Coder must update tests broken by legitimate implementation changes (expectation drift)

### Finding

After the Coder completed the PR #118 implementation, the test suite had six regressions. Three were test expectation drift — tests that were asserting incidental implementation details that the Coder's own changes made stale:

1. Savepoint naming changed (`critique_results_iteration_N` → `{mode}_critique_results_iteration_N`) — test expected old key.
2. Stdout output format changed — test checked old text.
3. Prompt count changed — test asserted old count.

All three were straightforward to fix by updating the test assertions. None represented bugs in the implementation. However, the Coder returned without fixing them, leaving regression cleanup to the Orchestrator's Step 5c pass.

### Observation

Rule 11 ("implement only listed files") guards against scope creep — the Coder must not make incidental improvements to code outside the dispatch scope. However, when the Coder's own implementation legitimately changes an output contract (savepoint key names, stdout formats, internal counts), tests asserting the old values are not "out of scope" — they are broken by the implementation. Updating them is not scope creep; it is completing the implementation.

The existing guidance does not distinguish between:
- Tests broken by the Coder's changes (expectation drift — Coder must fix)
- Tests that were already failing before the task (not Coder's responsibility)
- Tests that reveal bugs in the new implementation (fix the implementation, not the test)

Without explicit guidance, the Coder interprets Rule 11 as a blanket prohibition on test file edits and returns with knowable regressions unfixed.

This pattern is distinct from the collection assertion quality issue (issue #88) and independent expected value pinning (issue #89): those cover how tests should be written; this covers who is responsible for updating them when implementation changes break them.

### Suggested Improvement

Add a sub-bullet exception to Rule 11 in coder.agent.md clarifying that test expectation drift (tests the Coder's own implementation broke) must be fixed in the dispatch, even if test files are not listed in the plan.

### Action Taken

Applied: added "Test expectation drift" exception sub-bullet to Rule 11 of `.github/agents/coder.agent.md`.
