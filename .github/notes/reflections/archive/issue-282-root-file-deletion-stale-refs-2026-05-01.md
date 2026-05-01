---
date: "2026-05-01"
issue: 282
pr: 283
category: skill
targets:
  - ".agents/skills/documentation-maintenance/SKILL.md"
  - ".agents/skills/reflection/SKILL.md"
  - ".agents/skills/code-review/references/checklist.md"
  - ".agents/skills/synthesized-audit/SKILL.md"
  - ".github/agents-copilot/"
  - ".github/agents-openrouter/"
severity: minor
---

## Root File Deletions Leave Broken References in Skill and Agent Files

### Finding

PR #280 deleted five root-level files (`AGENTS.md`, `README.md`, `config-guide.md`, `Todo.md`, `requirements.txt`). PR #283 performed a mechanical text-substitution sweep across 12 files to repair broken references, but several out-of-scope stale references remain in the skill/agent system:
- `.agents/skills/documentation-maintenance/SKILL.md` lists `AGENTS.md` as a companion sweep target
- `.agents/skills/reflection/SKILL.md` lists `AGENTS.md` as a reflection target
- `.agents/skills/code-review/references/checklist.md` instructs updating `AGENTS.md`
- `.agents/skills/synthesized-audit/SKILL.md` instructs reading `AGENTS.md`
- Copilot (`agents-copilot/`) and OpenRouter (`agents-openrouter/`) agent files still reference `AGENTS.md` and `requirements.txt`

### Observation

Skill files themselves contain stale references to a deleted file, meaning agents dispatched to perform maintenance, audits, or reviews may be directed to a non-existent file. The companion sweep lists and checklists did not get updated when `AGENTS.md` was deleted. This suggests that file deletion PRs need an explicit "skill and agent instruction reference sweep" step, not just markdown link verification.

### Suggested Improvement

1. Remove `AGENTS.md` from all `.agents/skills/` sweep/target/check lists and replace with `.github/copilot-instructions.md` where appropriate.
2. Perform the same substitution sweep across `.github/agents-copilot/` and `.github/agents-openrouter/` agent files (out of scope for PR #283).
3. Add a general instruction to `documentation-maintenance/SKILL.md` that when root-level files are deleted, a full-repo grep should verify no skill or agent instruction still references them.

### Action Taken

Applied:
- Removed `AGENTS.md` from `documentation-maintenance/SKILL.md` companion sweeps
- Replaced `AGENTS.md` with `.github/copilot-instructions.md` in `reflection/SKILL.md` scope list
- Removed `AGENTS.md` from `code-review/references/checklist.md` update instruction

Deferred:
- `synthesized-audit/SKILL.md` still references `AGENTS.md` on line 50 — update to `.github/copilot-instructions.md` in a future dispatch
- Copilot/OpenRouter agent files need a dedicated sweep PR
