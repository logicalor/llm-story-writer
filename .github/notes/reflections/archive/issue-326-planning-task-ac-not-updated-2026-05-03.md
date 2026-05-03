---
date: "2026-05-03"
issue: 326
pr: 338
category: skill
targets:
  - ".agents/skills/documentation-maintenance/SKILL.md"
severity: minor
status: active
---

## Documenter Does Not Update Planning Task ACs After Implementation

### Finding

After PR #338 (issue #326) implemented Tasks 5 and 7 of the chromadb-source-sync plan, the task-level acceptance criteria checkboxes in `docs/planning/chromadb-source-sync/tasks.md` remained unchecked (`[ ]`). The same pattern occurred in PR #337 (issue #325) for Tasks 3 and 4. Only Tasks 1 and 2 (from PR #336) have their ACs correctly marked as `[x]` — and only because the tasks.md used "Status: Implemented in..." prose rather than checkboxes for those tasks.

The Documenter dispatched at the end of each PR did not update the planning task ACs. The `documentation-maintenance` SKILL.md contains no guidance about updating planning task checkboxes.

### Observation

Planning task documents (`docs/planning/*/tasks.md`) are read by agents during planning and sprint-running phases. Unchecked ACs for completed work lead agents to re-implement already-done features or waste time verifying whether work was done. The pattern repeated across three consecutive PRs (#336, #337, #338) on the same plan, confirming this is a systematic gap rather than a one-off miss.

### Suggested Improvement

Add a rule to the `documentation-maintenance` SKILL.md Rules section:

> When implementing tasks from a planning document (`docs/planning/*/tasks.md`), mark each completed acceptance criterion with `- [x]` and add or update the task's "**Status:**" line to reference the completing issue and PR number. Also update the PRD Status line at the top of the companion `prd.md`.

### Action Taken

Applied: added planning-task AC update rule to the Rules section of `.agents/skills/documentation-maintenance/SKILL.md`.
