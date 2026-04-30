---
date: "2026-04-30"
issue: 264
pr: 273
category: skill
targets:
  - ".agents/skills/documentation-maintenance/SKILL.md"
severity: minor
status: applied
---

## Documenter Skill Missing `.opencode/agents/` in Companion Sweep

### Finding

During issue #264 — a docs-only PR that only touched `.opencode/agents/*.md` files — the Orchestrator delegated to the Documenter as the primary implementer. The Documenter was supposed to edit the agent files directly but its Edit tool was blocked by permission rules despite `.opencode/agents/documenter.md` declaring `.opencode/agents/**: allow`.

### Observation

Two issues:

1. **Skill gap:** The `documentation-maintenance` SKILL.md "Companion Sweeps" list did not include `.opencode/agents/`, so the skill didn't instruct the Documenter to touch those files during sweeps.
2. **Subagent runtime discrepancy:** The Documenter subagent's own YAML already had `.opencode/agents/**: allow`, yet the tool execution layer still rejected the edit. This suggests the permission enforcement layer may differ from the agent YAML — possibly a sandbox/skill-scope override.

### Suggested Improvement

- The skill itself should tell the Documenter to sweep `.opencode/agents/` when agent-family config changes (already applied in PR #273).
- Investigate whether the subagent edit permission rejection was a transient sandbox issue or a systematic mismatch between agent YAML declarations and actual tool enforcement.

### Action Taken

- Applied: Added `.opencode/agents/` to the `documentation-maintenance` skill companion sweep list, with a note that it is the canonical source for agent-family config changes.

### Verification of fix

- Edited `.agents/skills/documentation-maintenance/SKILL.md` — lines 37–39 now include `.opencode/agents/`.
- No ChromaDB embedding performed (tool unavailable in this session).
