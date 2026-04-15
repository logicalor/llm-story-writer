---
date: "2026-04-15"
issue: 19
pr: 63
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: active
---

## Stale count pattern — eighth occurrence ("Four skills" when three existed)

### Finding

During issue #19 (Build Scene Writer Subagent), the Coder/Documenter wrote "Four skills" in the story-orchestrator feature doc when only three skills existed. This was caught by the Synthesized Review as U-W-01 and fixed in the review-fix cycle.

### Observation

This is the **eighth** occurrence of the stale-count pattern across issues #4, #5, #11, #12, #30, #13, #17, and #19. The issue #13 reflection established that this is an **accuracy** problem, not a compliance problem — the Coder is attempting the count but getting it wrong. The issue #17 reflection added inventory table cross-checking to the Documenter.

This occurrence has a slight variant: the agent was writing a *new* file (not updating an existing count), and the count was wrong from initial authoring — likely a simple miscount of deliverables during composition, counting an item that hadn't been created yet or double-counting.

No rule text change is warranted. The review system catches this reliably (8 for 8). The cost per occurrence is one review-fix cycle.

### Suggested Improvement

No rule change. Recording for continued tracking evidence.

### Action Taken

No action needed — recurrence of known pattern recorded for evidence.
