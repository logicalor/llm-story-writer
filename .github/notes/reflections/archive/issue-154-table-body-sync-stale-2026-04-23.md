---
date: "2026-04-23"
issue: 154
pr: 155
category: instruction
targets:
  - ".github/agents/_shared/code-review-process.md"
  - ".github/agents/coder.agent.md"
severity: minor
status: active
---

## Summary tables go stale relative to body text when agent files are edited

### Finding

`story-orchestrator.md` contains a "Per-Chapter Required Sequence" summary table that
restates the phase-by-phase file operations as a lookup reference. Phase 7e's body text was
updated to explicitly say "do NOT write `chapter_{N}.md`", but the summary table still said
"Write `chapter_{N}.md`" for Phase 7e. Agents following the table over the body text would
write the wrong file.

### Observation

Summary tables in agent/skill files are secondary restatements of body prose. When body prose
changes, editors update the prose but rarely scroll to find and update the corresponding table
row. The result is a silent contract mismatch: careful agents following the table do the wrong
thing; the contradiction is only visible if both sections are read together.

This pattern is distinct from the existing "stale prose counts" check (which covers numeric
counts) and the "story-pipeline SKILL.md sync" check (which covers a specific known file). It
applies broadly to any agent/skill file that uses a table as a summary of steps or operations.

### Suggested Improvement

Add a Phase 1 review checklist item to `code-review-process.md`:

> **Summary table vs body text parity** — when any agent or skill file that contains a summary
> table is edited, re-read every Markdown table in the file and verify its rows match the body
> text. Tables are commonly out of sync because editors update prose but do not scroll to update
> the corresponding table row.

Also add a mirror bullet to the Coder agent's Rule 6 (text sweep section) so Coders also check
this before handing off.

### Action Taken

Applied: added checklist item to Phase 1 of `.github/agents/_shared/code-review-process.md`
and a mirror bullet to `.github/agents/coder.agent.md` Rule 6.
