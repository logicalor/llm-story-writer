---
date: "2026-04-16"
issue: 21
pr: 66
category: agent
targets:
  - ".github/agents/orchestrator-v3.agent.md"
severity: minor
status: active
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
