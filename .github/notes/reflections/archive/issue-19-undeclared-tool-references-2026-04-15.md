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

## Agent definition references tools in prose but omits them from tools table

### Finding

During issue #19 (Build Scene Writer Subagent), the `.opencode/agents/chapter-writer.md` agent definition referenced `character-mgr` and `setting-mgr` as fallback tools in its workflow prose but did not list them in the tools table. The Synthesized Review caught this as U-W-02 — the tools table was incomplete relative to the workflow text.

### Observation

This is an internal consistency issue within a single authored file — the prose section and the tools table diverge. It's related to the stale-count pattern (issue #17's inventory table cross-check) but the variant is different: here the source of truth is the *same file's own prose*, not files on disk. The Documenter's existing Step 3 verification bullet covers cross-checking tables against files on disk, but doesn't explicitly cover cross-checking an agent definition's tools table against its own workflow prose.

This is a minor oversight easily caught by review and unlikely to cause runtime failures (tools not in the table are still available if declared in `opencode.json`). The cost is one review-fix cycle.

### Suggested Improvement

No rule change. The existing inventory verification bullet in the Documenter's Step 3 is close enough — extending it to cover intra-file consistency would over-specify the checklist. The review system catches this reliably.

### Action Taken

No action needed — recording for pattern tracking.
