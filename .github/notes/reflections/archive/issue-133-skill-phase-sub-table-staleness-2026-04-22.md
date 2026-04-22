---
date: "2026-04-22"
issue: 133
pr: 137
category: instruction
targets:
  - ".github/agents/_shared/code-review-process.md"
severity: minor
status: archived
---

## story-pipeline SKILL.md sub-phase table stale when orchestrator phase workflow changes

### Finding

During PR #137, the Phase 7g implementation was simplified from four inline orchestrator
steps (using `prompt-loader`, `story-state`, `savepoint-mgr` directly) to a single
`story-assembler` tool call. The `story-pipeline/SKILL.md` sub-phase table for Phase 7g
initially still listed `prompt-loader, story-state, savepoint-mgr` as the tools — only the
Phase 7g row in the tools column was wrong. Claude's review surfaced this as S-W-01
(Warning). GPT also flagged the tool registry description was stale. The fix was applied
before merge.

### Observation

The existing `code-review-process.md` Phase 1 checklist item **"story-pipeline SKILL.md sync
for new pipeline subagents"** only triggers on **new** subagent additions to the pipeline.
It does not trigger on changes to how an **existing** phase uses tools. When a phase is
refactored to use a different tool (or fewer tools), the sub-phase table is a companion file
that silently drifts.

The "Companion file concept sweep" item triggers on "tool operation name, parameter name, or
return format" changes — but not on phase workflow simplification (removing inline steps in
favour of a single tool call). Both checklist items have a coverage gap for this case.

Any agent loading a stale sub-phase table will be misled about which tools to expect Phase 7g
to use, affecting debugging and orchestration reasoning.

### Suggested Improvement

**`code-review-process.md` Phase 1 — extend the story-pipeline SKILL.md sync item** to cover
existing phase workflow changes:

Add after the existing bullets: "Also trigger when any phase steps in `story-orchestrator.md`
are changed (phase simplified, tools replaced, steps reorganised) — read the corresponding
row in the Phase 7 sub-phase table and verify the Tools/Subagents column accurately reflects
the updated tool set. (Source: issue #133, PR #137 — Phase 7g simplified from inline steps to
single `story-assembler` call; sub-phase table initially still listed the old tools.)"

### Action Taken

Applied: Extended the story-pipeline SKILL.md sync checklist item in `code-review-process.md`
to include existing phase workflow changes as a trigger.
