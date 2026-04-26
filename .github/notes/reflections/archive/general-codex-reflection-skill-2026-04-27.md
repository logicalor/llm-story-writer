---
date: "2026-04-27"
issue: general
pr: none
category: skill
targets:
  - ".agents/skills/reflection/SKILL.md"
  - ".agents/skills/github-workflow/SKILL.md"
  - "AGENTS.md"
severity: major
status: archived
---

## Codex reflection skill added

### Finding

The Copilot agent system had `.github/agents/reflection.agent.md` for recording and applying improvements to agents, skills, instructions, and reflection notes. The Codex workflow skill set did not have an equivalent dedicated skill.

### Observation

Without a Codex-native reflection skill, future Codex sessions had to infer the reflection process from the legacy Copilot agent or skip durable agent-system improvement capture. This left the GitHub workflow without an explicit checkpoint for reusable gotchas, stale instructions, and safe workflow instruction updates.

### Suggested Improvement

Create `.agents/skills/reflection/SKILL.md` as the Codex-native counterpart, incorporate it into `.agents/skills/github-workflow/SKILL.md`, and list it in `AGENTS.md` with the other Codex workflow skills.

### Action Taken

Applied: Added the `reflection` skill, added reflection checkpoints and output reporting to the `github-workflow` skill, and listed the new skill in `AGENTS.md`. The change was explicitly requested by the user, so the major workflow update was applied directly.
