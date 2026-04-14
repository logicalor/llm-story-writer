---
date: "2026-04-14"
issue: 15
pr: 54
category: instruction
targets:
  - ".github/notes/gotchas.md"
severity: minor
status: active
---

## O(n²) token recalculation in budget enforcement loop

### Finding

During issue #15 (Build wiki-snapshot Tool), the token budget enforcement loop recalculated total tokens from scratch on every iteration instead of maintaining a running total. For large page sets, this creates O(n²) complexity. The Synthesized Review flagged this as a Warning.

### Observation

This is a classic algorithmic pattern: when greedily selecting items within a budget, recalculating the aggregate from scratch each iteration instead of incrementally updating a running total. The fix is trivial (maintain `current_total += item_cost` instead of `sum(costs)` each loop), but it's easy to miss during initial implementation because correctness is unaffected — only performance suffers.

This would be a good candidate for the `gotchas.md` file (when created per issue #7 proposal) under an "Algorithmic Patterns" section.

### Suggested Improvement

When `gotchas.md` is created (issue #7 dependency), add this entry:

```markdown
### Running Total in Budget/Greedy Loops

**Wrong:** `total = sum(item.cost for item in selected)` inside the selection loop — O(n²).
**Right:** `total += candidate.cost` when adding, `total -= removed.cost` when removing — O(n).

Any loop that greedily selects items within a budget should maintain a running total, not recalculate from the full set each iteration.
```

### Action Taken

No action taken — target file (`gotchas.md`) does not exist yet. Recorded for inclusion when the conventions collection is created (issue #7 dependency).
