---
date: "2026-04-13"
issue: 11
pr: 36
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## Documentation counts go stale when adding items to a counted set

### Finding

During issue #11 (Build setting-mgr Tool), `architecture.md` said "Four tools" when there were now five. The Synthesized Review caught this as U-W-01 (unanimous). This is a variant of the recurring stale-docs pattern (issues #4, #5, #30) — but those were about renamed/relocated paths, while this is about numeric counts becoming stale when a new item is added to a category.

### Observation

Coder Rule 6 triggers on text sweeps (renaming, relocating, removing). It does not explicitly cover the case where *adding* a new item to a counted set (tools, collections, agents, etc.) causes an existing count in docs to become stale. The Coder isn't searching-and-replacing anything — they're adding something new, and a numeric literal elsewhere becomes wrong.

The fix is narrow: extend Rule 6's trigger conditions to include "adding or removing items from a counted/inventoried set."

### Suggested Improvement

Add to Coder Rule 6, after the existing text:

```markdown
Also, **when adding or removing an item** from a set that may be counted or inventoried in documentation (tools, collections, agents, prompt categories), grep for the old count (e.g., "Four tools", "4 tools") across docs to update it.
```

### Action Taken

Applied: extended Coder Rule 6 with counted-set staleness check.
