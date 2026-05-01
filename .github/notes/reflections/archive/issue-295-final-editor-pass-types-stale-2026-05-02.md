---
date: "2026-05-02"
issue: 295
pr: 307
category: skill
targets:
  - "prompts/skills/final-edit/SKILL.md"
  - "prompts/agents/story-orchestrator.md"
  - "prompts/agents/final-editor.md"
severity: minor
---

## `final-editor` prose-scrub diagnostics absent from SKILL.md Pass Types table and Phase 9 spec

### Finding

After PR #307 wired `enable_scrubbing` into `FinalEditorAgent` as a two-stage diagnostic
flow, two documents still omit the change:

1. `prompts/skills/final-edit/SKILL.md` — the Pass Types table lists "Prose Scrub" with
   only `prose-scrubber` as the agent. `final-editor` now runs prose-scrub diagnostics
   as Stage 1a when `settings.enable_scrubbing` is `true`, but the table makes no mention
   of this.

2. `prompts/agents/story-orchestrator.md` — Phase 9 dispatch notes do not mention
   `enable_scrubbing` or the Stage 1a/1b pre-pass. An agent following the orchestrator
   prompt would dispatch `final-editor` without knowing that passing
   `config.generation.enable_scrubbing: true` activates the diagnostic flow.

A third document (`prompts/agents/final-editor.md`) is the OpenCode workflow spec. Its
Workflow section has no `enable_scrubbing` conditional steps (Stage 1a prose scrub,
Stage 1b voice pass). This is a larger structural change and is classified as major.

### Observation

The pattern from issue #294 (`stale-description-after-adding-API`) recurs: when a
pipeline stage gains new optional behaviour gated by a config flag, the skill table and
the orchestrator dispatch note often remain at the pre-feature baseline. Readers consulting
only the SKILL.md or the orchestrator prompt would believe prose-scrub diagnostics are
exclusively a Phase 7.5 concern (prose-scrubber subagent, not yet wired), unaware that
`enable_scrubbing: true` already activates them in Phase 9.

### Suggested Improvement

**Minor (targets 1 and 2 — apply immediately):**

1. `prompts/skills/final-edit/SKILL.md` — update the Prose Scrub row in the Pass Types
   table to include `final-editor` as the Stage 1a agent when `enable_scrubbing: true`.
2. `prompts/agents/story-orchestrator.md` — Phase 9 dispatch block: add a bullet noting
   that `final-editor` runs prose-scrub and voice-consistency diagnostics (Stage 1a/1b)
   before each chapter edit when `config.generation.enable_scrubbing` is `true`.

**Major (target 3 — propose for approval):**

3. `prompts/agents/final-editor.md` — add `enable_scrubbing` conditional steps 3a/3b to
   the Workflow section so an OpenCode `final-editor` dispatch performs the Stage 1
   diagnostic passes (load `prompts/final_edit/prose_scrub.md`, call model, collect
   `prose_findings`; load `prompts/final_edit/voice_consistency_pass.md`, call model,
   collect `voice_findings`) and injects them into the Stage 2 `edit_chapter_direct` call.
   This is a structural addition to the workflow and could affect downstream OpenCode runs.

### Action Taken

Applied (minor):
- Updated `prompts/skills/final-edit/SKILL.md` Prose Scrub row to list both
  `prose-scrubber` and `final-editor` (Stage 1a, when `enable_scrubbing: true`).
- Updated `prompts/agents/story-orchestrator.md` Phase 9 dispatch block to mention
  the `enable_scrubbing` Stage 1a/1b diagnostic pre-pass.

Proposed (major):
- `prompts/agents/final-editor.md` Workflow — add `enable_scrubbing` Stage 1a/1b steps.
  Awaiting approval before applying.
