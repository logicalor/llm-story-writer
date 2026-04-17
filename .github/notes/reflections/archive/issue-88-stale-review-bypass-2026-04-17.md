---
date: "2026-04-17"
issue: 88
pr: 91
category: agent
targets:
  - "/memories/orchestrator-issues.md"
severity: minor
status: archived
---

## Stale user memory caused unnecessary synthesized review bypass

### Finding

During issue #88 (Integration test: wiki-read path has no coverage), the Orchestrator bypassed the 3-reviewer synthesized review and used a single Claude reviewer instead, citing "the known VS Code stability issue noted in user memory."

The user memory at `/memories/orchestrator-issues.md` still contains the old workaround note from issue #68:

> "Dispatching 3 parallel reviewer subagents causes VS Code window to become non-responsive. Workaround: do single-pass direct review instead of Synthesized Review."

However, this problem was **fully resolved** in PR #70 (issue #68) via the flattened dispatch architecture:
- The Orchestrator now dispatches all three reviewers **sequentially** (depth-1) and each writes a report to disk
- The Synthesizing Reviewer reads the pre-written reports — it no longer dispatches sub-agents
- This architecture was validated in PR #70 as the definitive resolution

The user memory was supposed to be updated to reflect this resolution (the archive note from issue #68 explicitly states "User memory updated to reflect resolution"), but the update was never actually applied.

### Observation

Stale memory caused the review pipeline to silently degrade. The Orchestrator read old workaround guidance that has been superseded, and used a single reviewer instead of the full synthesized review. This reduced review quality for PR #91 without any actual need — the flattened architecture should have prevented the freeze.

Keeping user memory accurate is as important as keeping agent files accurate. Stale workaround notes persist as operational risk.

### Suggested Improvement

Update `/memories/orchestrator-issues.md` to accurately reflect the current state: the VS Code freeze issue was resolved in PR #70 via the flattened architecture. The workaround note should be replaced with a resolved status and a reference to the flattened architecture.

### Action Taken

Applied: updated the user memory file at the actual path (`/home/shaun/.config/Code/User/globalStorage/github.copilot-chat/memory-tool/memories/orchestrator-issues.md`) to mark the issue as resolved and document the flattened architecture fix.
