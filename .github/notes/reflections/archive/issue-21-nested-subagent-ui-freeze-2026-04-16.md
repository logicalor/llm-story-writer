---
date: "2026-04-16"
issue: 21
pr: 66
category: agent
targets:
  - ".github/agents/orchestrator-v3.agent.md"
severity: minor
status: archived
---

## VS Code UI freezes from nested subagent dispatch during Synthesized Review

### Finding

During issue #21 (Build Custom Commands), the Orchestrator's multi-step workflow with nested subagents (Orchestrator → Synthesizing Reviewer → 3× independent Reviewers) caused VS Code UI freezes. The accumulated conversation size from 4+ levels of agent nesting and rapid tree view updates overwhelmed the VS Code Copilot Chat runtime.

The user's `chat.agent.maxRequests: 500000` setting removed the built-in request guardrails, allowing the conversation to grow unbounded until the UI became unresponsive.

### Observation

This is a VS Code Copilot Chat runtime limitation, not an agent instruction defect. The agent architecture (Orchestrator → Synthesizing Reviewer → 3× sub-reviewers) is correct by design — each level serves a distinct purpose. The UI freeze is caused by the platform's inability to handle the accumulated context size and rapid tool invocations within a single VS Code chat session.

The `maxRequests` setting is user-controlled and outside agent instruction scope. However, the pattern is worth monitoring: as the agent system adds more nested dispatches (subagents within subagents), the conversation size grows multiplicatively, increasing the likelihood of hitting platform limits.

No actionable agent instruction change exists for this — the fix would need to come from VS Code Copilot Chat's conversation management (context windowing, lazy rendering, background dispatch).

### Suggested Improvement

No agent instruction change. Record as an operational observation for the user: setting `chat.agent.maxRequests` to very high values (500000) removes all guardrails and can cause UI freezes with deeply nested agent workflows. A more moderate value (e.g., 200) would provide a safety net while still allowing the full workflow to complete.

### Action Taken

No action needed — runtime platform limitation, not an agent system defect. Recorded for awareness.

**Update (issue #23):** An agent-level mitigation was found and applied — the "review package pre-compute" pattern (Step 0 in Synthesizing Reviewer) collects all data once before dispatching sub-agents, eliminating ~60% of redundant tool calls. See `issue-23-review-package-precompute.md`.

**Update (issue #68, PR #70):** Fully resolved. The Orchestrator's Step 7 was refactored to a flattened depth-1 architecture (Option D). All three reviewers are dispatched sequentially by the Orchestrator and write reports to disk. The Synthesizing Reviewer reads the files — no sub-agent dispatch. First successful Synthesized Review without UI freezes. See `issue-68-flattened-review-architecture-validated.md`.
