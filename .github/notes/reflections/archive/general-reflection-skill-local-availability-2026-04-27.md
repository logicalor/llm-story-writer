---
date: "2026-04-27"
issue: general
pr: none
category: skill
targets:
  - ".agents/skills/github-workflow/SKILL.md"
  - ".agents/skills/reflection/SKILL.md"
severity: minor
status: archived
---

## Reflection skill local availability

### Finding

During a Codex GitHub workflow run, the reflection step skipped creating a reflection note with the explanation that `.agents/skills/reflection/SKILL.md` was not present on `origin/development`.

### Observation

Skill availability should be determined from the current workspace, not from whether the skill has already merged to the remote base branch. New workflow skills often need to be usable on the same branch that introduces them.

### Suggested Improvement

Clarify in the GitHub workflow and reflection skill instructions that locally present skill files are available for the current session even when they are new on the branch or absent from `origin/development`.

### Action Taken

Applied: Added local-availability guidance to `.agents/skills/github-workflow/SKILL.md` and `.agents/skills/reflection/SKILL.md`.
