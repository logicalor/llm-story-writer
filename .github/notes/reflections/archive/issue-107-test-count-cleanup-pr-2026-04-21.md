---
date: "2026-04-18"
issue: 107
pr: 108
category: agent
targets:
  - ".github/agents/orchestrator-v3.agent.md"
severity: minor
status: archived
---

## Test count changes on cleanup PRs are expected, not regressions

### Finding

After PR #108 (42k-deletion cleanup), pytest reported 326 passed + 14 skipped, down from 340
collected previously. The 14 skipped tests and reduced collection count traced directly to the
deleted root-level `test_*.py` files, which were previously being discovered by pytest (despite
being outside `testpaths = ["tests/unit"]`) and to legacy shim methods removed from
`rag_integration_service.py`.

The Orchestrator correctly identified the change as expected — not a regression — by tracing the
skipped tests back to the deleted code.

### Observation

Orchestrator Step 5c requires "zero failures, zero unexpected skips, linting clean." The word
"unexpected" is doing important work here, but the step does not explain how to classify a skip
as "unexpected."

For standard feature-addition PRs, any skip is unexpected by default (no code was removed, so
skips shouldn't appear). For deletion/cleanup PRs, a reduction in collection count and/or new
skipped tests is a predictable consequence of removing code those tests covered. The Orchestrator
handled this correctly, but the reasoning ("trace each skip to deleted code") is not documented
— it depends on the agent intuitively applying the right classification.

Documenting the classification heuristic explicitly:
- **Unexpected skip:** a skip that cannot be traced to a file, method, or class deleted in this PR
- **Expected skip:** a skip directly traceable to deleted code

This is particularly relevant for large deletion/cleanup PRs where 10+ file removals make manual
review error-prone.

### Suggested Improvement

Add a clarifying note to Step 5c ("zero unexpected skips") in
`.github/agents/orchestrator-v3.agent.md`:

> **For deletion/cleanup PRs:** a reduction in collection count or new skipped tests is expected
> when test files or tested methods were deleted. Classify a skip as "unexpected" only if it
> cannot be traced to a file, method, or class removed in this PR. Verify by checking the skip
> reason or test name against the deleted code scope.

### Action Taken

Applied: added clarifying note to Step 5c in `.github/agents/orchestrator-v3.agent.md`.
Embedded this reflection into the `reflections` ChromaDB collection.
