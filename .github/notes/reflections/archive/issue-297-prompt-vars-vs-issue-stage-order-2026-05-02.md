---
date: "2026-05-02"
issue: 297
pr: 309
category: instruction
targets:
  - ".github/agents/_shared/review-checklist.md"
severity: minor
---

## Prompt variable names define correct stage order when issue description conflicts

### Finding

During issue #297 (PR #309, RecapWriterAgent), the issue description specified processing
stages in the wrong order (enrich before timing). The prompt templates used `{timed_events}`
as an input variable to the enrich stage, which unambiguously required timing to run first
— but the issue text said the opposite. The Coder proceeded with the order the prompt
variables dictated, which was correct.

### Observation

An issue description is written prose; prompt variable names are executable contracts.
When an issue description specifies stage A before stage B, but the prompt for stage A
accepts `{stage_B_output}` as an input variable, the prompt variables define the correct
order — the issue description is wrong. Without a review check calling this out, an agent
following the issue description literally would wire the stages backwards, producing a
silent but semantically wrong pipeline.

### Suggested Improvement

Add a bullet to Phase 2 Agent Instructions in `.github/agents/_shared/review-checklist.md`
prompting reviewers to cross-check prompt template variable names against any stage ordering
described in the issue or agent instructions, and trust the prompt variables when they conflict.

### Action Taken

Applied:
- Added `Prompt variable names override issue description stage ordering` check to Phase 2
  Agent Instructions in `.github/agents/_shared/review-checklist.md`, after the
  "Intra-step variable cross-reference" bullet.
