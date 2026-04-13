---
date: "2026-04-14"
issue: 9
pr: 44
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: active
---

## Coder leaves dead code in new shared module

### Finding

During issue #9 (Build recap-manager Tool), the Coder created `src/tools/_llm.py` as a shared LLM client module. The initial implementation included a `_call_llm_json()` function that was never called anywhere — it was dead code from an abandoned approach. Synthesized Review caught it as U-W-01, and it was removed during review fixes.

### Observation

This is a different class of cleanup gap from Rule 7 (temp files). Rule 7 says "delete all temporary or investigation files created during the task." Dead code within production files isn't a temp file — it's an artifact of iterative development where the Coder writes a helper, changes approach, and forgets to remove the unused function.

Linters (ruff) catch unused variables and imports, but not unused top-level functions — those require manual inspection or a callers check. The Coder should do a quick sweep of new files for unused functions before handoff, similar to how Rule 6 requires grepping for stale references.

This is low-severity because the Synthesized Review reliably catches it, but catching it pre-handoff saves a review-fix cycle.

### Suggested Improvement

Expand Coder Rule 7 to include dead code sweep alongside temp file cleanup:

```markdown
7. **Before returning to the Orchestrator**, delete all temporary or investigation files created during the task. Also sweep newly created or heavily modified files for dead code — unused functions, unreachable branches, abandoned helpers — especially in shared modules where iterative development leaves artifacts.
```

### Action Taken

Applied: expanded Coder Rule 7 to include dead code sweep alongside temp file cleanup.
