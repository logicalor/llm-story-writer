---
date: "2026-04-14"
issue: 15
pr: 54
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: major
status: active
---

## Cache populated but never wired to consumer — illusory optimization

### Finding

During issue #15 (Build wiki-snapshot Tool), the Coder implemented a delta cache that correctly tracked cache hits/misses and stored `rendered_content` for previously-seen pages. However, the assembly stage that consumed pages never checked the cache — it always re-rendered from scratch. The Synthesized Review flagged this as Critical: the cache existed but provided zero performance benefit.

Tests verified cache statistics (hit/miss counts) but never asserted that cached content appeared in assembled output, so the disconnect was invisible to the test suite.

### Observation

This is a "wiring bug" variant of the issue #10 semantic correctness gap — all components exist and work individually, but the data flow between them is broken. Specifically:

1. **Cache write path:** Implemented correctly — pages are rendered and stored in the delta cache.
2. **Cache read path:** Never implemented — the assembly function bypasses the cache entirely.
3. **Tests:** Verified the cache's internal state but not its integration with consumers.

This is the **fourth** wiring bug pattern observed:
- Issue #10: `cmd_refine()` accepted `--feedback` but never passed it to the LLM
- Issue #46: Savepoint ordering inconsistent between similar operations
- Issue #12: Dead code from template-copying (components exist but aren't connected)
- Issue #15: Cache populated but never read by its consumer

The proposed semantic verification rule (issue #10) would catch this if it explicitly mentions **verifying that optimization/caching layers are actually integrated with their consumers**, not just individually functional.

### Suggested Improvement

Strengthen the proposed semantic verification rule (issue #10 proposal) to explicitly cover caching and optimization layers. When the rule is applied, add this example:

```markdown
Pay special attention to caching/optimization layers — verify the consumer actually reads from the cache, not just that the cache is populated. Tests that only check cache statistics (hits/misses) without verifying cached content reaches the output are insufficient proof of integration.
```

This is an addendum to the issue #10 proposal (still pending approval), not a separate rule.

### Action Taken

Recorded as supporting evidence for the pending issue #10 semantic verification rule proposal. The addendum should be included when that proposal is applied.
