---
date: "2026-04-15"
issue: 18
pr: 64
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: active
---

## Schema verification lesson from issue #19 successfully applied — first confirmation

### Finding

During issue #18 (Build Outline Planner Subagent), the Coder verified all tool parameter names against actual Zod schemas in `.opencode/tools/*.ts` before writing the agent definition. No parameter fabrication occurred — the first issue where this defect class was absent after being identified in issue #19.

### Observation

This is the **first positive confirmation** that the schema fabrication lesson (issue #19 reflection) carries forward without a formal numbered rule. The Coder's self-correction mirrors the pattern seen with security rules (issue #3): after a defect is caught and discussed, the Coder avoids it in the next task even before a formal rule is codified.

However, the issue #6 pattern amnesia experience shows that informal carry-forward is unreliable over multiple issues — the Coder stopped applying atomic writes after a few issues until Rule 9 formalised the requirement. The pending Rule 10/11 proposal (schema verification) remains valuable as a formal backstop even though the lesson was applied this time.

This positive signal strengthens the case for the pending issue #19 proposal but does not eliminate the need for it.

### Suggested Improvement

No new rule needed. Recording as supporting evidence for the pending issue #19 schema verification rule proposal, noting that informal carry-forward worked this time but formal codification is still recommended based on the issue #6 precedent.

### Action Taken

No action needed — positive signal recorded for evidence tracking.
