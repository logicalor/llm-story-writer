---
date: "2026-05-01"
issue: 282
pr: 283
category: agent | skill
targets:
  - ".github/agents-copilot/documenter.agent.md"
  - ".agents/skills/documentation-maintenance/SKILL.md"
  - ".agents/skills/reflection/SKILL.md"
  - ".agents/skills/code-review/references/checklist.md"
  - ".agents/skills/synthesized-audit/SKILL.md"
severity: minor
---

## Deleted Root-Level Files Leave Stale References in Skill and Agent Instructions

### Finding

PR #280 deleted five root-level files: `AGENTS.md`, `README.md`, `config-guide.md`, `Todo.md`, and `requirements.txt`. PR #283 swept broken references across 12 files (docs, `.opencode/agents/`, `opencode.json`, `src/`, `tests/`) but did not touch the Copilot-side documenter agent or the `.agents/skills/` directory. The review synthesis independently identified these stale references as fast-follow items.

### Observation

Skills and agent instructions that are themselves loaded at runtime now direct agents to files that no longer exist:

1. `.github/agents-copilot/documenter.agent.md` line 77 still tells the Documenter to "check `AGENTS.md`" for agent-family configuration claims. `AGENTS.md` is deleted.
2. `.github/agents-copilot/documenter.agent.md` line 79 still tells the Documenter to update `README.md` at the repo root. The root `README.md` is deleted; canonical docs are now in `docs/manual.md`.
3. `.github/agents-copilot/documenter.agent.md` lines 85 and 93 list `AGENTS.md` in the "companion-document sweep" and include it in the `grep` command.
4. `.agents/skills/documentation-maintenance/SKILL.md` line 29 references `AGENTS.md`.
5. `.agents/skills/reflection/SKILL.md` lines 20 and 40 reference `AGENTS.md`.
6. `.agents/skills/code-review/references/checklist.md` line 26 references `AGENTS.md`.
7. `.agents/skills/synthesized-audit/SKILL.md` line 50 references `AGENTS.md`.

These are self-referential stale references: the agents and skills tasked with keeping documentation fresh are themselves carrying broken pointers. If a future Documenter is dispatched to update architecture docs, it will grep a non-existent file and potentially skip valid references in the remaining companion files.

### Suggested Improvement

- **Immediate (minor):** Update the seven stale references listed above to point to the surviving canonical documents (`docs/features/opencode-runtime.md` for agent-family runtime descriptions; `docs/manual.md` for the former README role).
- **Structural (major):** Expand the `documentation-maintenance` skill companion sweep to explicitly include `.github/agents-copilot/`, `.github/agents-openrouter/`, and `.agents/skills/` when root-level project files are deleted. The current sweep covers `docs/` and `.opencode/agents/` but misses the legacy runtime agents and the skill definitions themselves.

### Action Taken

Applied: Updated `.github/agents-copilot/documenter.agent.md`:
- Line 77: `AGENTS.md` → `docs/features/opencode-runtime.md` for agent-family config claims.
- Line 79: `README.md` at repo root → `docs/manual.md` for UI-visible changes.
- Lines 85 and 93: removed `AGENTS.md` from the companion-document sweep list and grep command.

Remaining `.agents/skills/` stale references deferred to fast-follow. Structural companion-sweep expansion proposed for approval.
