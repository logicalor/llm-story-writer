---
date: "2026-04-16"
issue: 23
pr: 67
category: agent
targets:
  - ".github/agents/synthesizing-reviewer.agent.md"
  - ".github/agents/_shared/multi-model-synthesis.md"
severity: minor
status: archived
---

## Review package pre-compute pattern eliminates redundant I/O across sub-agents

### Finding

During issue #23 (Build Compaction Plugin), the Synthesizing Reviewer caused VS Code "window not responding" during the review phase. Root cause: each of the three reviewer sub-agents independently ran the same git commands (`git diff`, `git log`, file reads) — tripling tool-call volume and overwhelming the extension host.

This is a practical evolution of the issue #21 finding (nested subagent UI freeze), which was recorded as "no action needed — runtime platform limitation." Issue #23 proved that an actionable agent-level mitigation exists.

### Observation

The fix — adding Step 0 (Prepare Review Package) to the Synthesizing Reviewer — collects all data once in the coordinator context, then passes a pre-assembled text block to each sub-agent. Sub-agents use the provided data instead of re-running commands.

Impact was significant: eliminated ~60% of tool calls during the review phase and resolved the VS Code stability issue entirely for this workflow. The pattern was generalised into `.github/agents/_shared/multi-model-synthesis.md` as a "Pre-Compute Shared Data" section, making it available to all synthesizing agents (Synthesizing Auditor, Synthesizing Researcher).

This is the strongest mitigation available at the agent instruction level for the platform limitation identified in issue #21.

### Suggested Improvement

No further agent instruction change needed — the fix was applied during the task. Both the specific implementation (Step 0 in `synthesizing-reviewer.agent.md`) and the generalised pattern (in `multi-model-synthesis.md`) are already in place.

### Action Taken

Applied during issue #23: added Step 0 (Prepare Review Package) to Synthesizing Reviewer and Pre-Compute Shared Data section to multi-model-synthesis.md. Supersedes issue #21 conclusion of "no action needed."
