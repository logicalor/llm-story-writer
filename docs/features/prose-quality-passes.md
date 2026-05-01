# Prose Quality Passes

> Conditional prose-polish layers for chapter cleanup and late-stage manuscript editing.

## Overview

Issue #121 and PR #128 introduced two prose-quality surfaces: `prose-scrubber` and `final-editor`. Issue #185 / PR #198 replaced the old Phase 9 stub with a real `FinalEditorAgent` execution path in `src/presentation/orchestrator.py`, and issue #295 / PR #307 wired `enable_scrubbing` into that agent as a diagnostic pre-pass.

`final-editor` now runs after the chapter loop and before assembly. It sends one approved chapter at a time through a streamed LLM edit pass, preserves the original chapter if the model returns empty output, updates `state.approved_chapters`, and writes `stories/<name>/output/story_edited.md` before `story.md` is assembled.

When `generation.enable_scrubbing` is `true`, `FinalEditorAgent` runs two Stage 1 diagnostics before the chapter polish pass: `prompts/final_edit/prose_scrub.md` produces `prose_findings`, and `prompts/final_edit/voice_consistency_pass.md` produces `voice_findings`. Stage 2 then injects both findings into `prompts/final_edit/edit_chapter_direct.md`. When `enable_scrubbing` is `false`, Stage 1 is skipped and Stage 2 receives empty strings, preserving the earlier final-edit behavior. Neither path replaces the chapter approval gate.

## Pipeline Placement

| Pass | Agent | Pipeline Position | Trigger | Scope |
|------|-------|-------------------|---------|-------|
| Prose Scrub Diagnostics | `final-editor` | Phase 9 Stage 1a, before chapter polish | `generation.enable_final_edit` not explicitly `false` and `generation.enable_scrubbing: true` | Sentence and paragraph findings |
| Voice Consistency Diagnostics | `final-editor` | Phase 9 Stage 1b, before chapter polish | `generation.enable_final_edit` not explicitly `false` and `generation.enable_scrubbing: true` | Voice and prior-chapter consistency findings |
| Final Edit | `final-editor` | Phase 9 Stage 2, after diagnostics and before assembly | `generation.enable_final_edit` not explicitly `false` | One accepted chapter at a time |

The passes are complementary:

- `quality-reviewer` is still a separate concept from prose polishing.
- `prose-scrub` and `voice-consistency` prompts now run as internal `final-editor` diagnostics, not as standalone orchestrator phases.
- `final-editor` remains the only prose-quality phase directly invoked by the Python-native orchestrator.

## User Guide

Enable or disable the passes in the `generation` config block.

```yaml
generation:
  enable_scrubbing: true
  enable_final_edit: true
```

Current behavior in `src/presentation/orchestrator.py` and `src/presentation/agents/final_editor.py`:

- `enable_final_edit` skips Phase 9 only when the value is explicitly `false`
- if the key is missing from the raw `generation` config mapping, the orchestrator treats final-edit as enabled
- `enable_scrubbing: true` runs Stage 1a/1b diagnostic prompts before the chapter polish pass
- `enable_scrubbing: false` skips those diagnostics and passes empty findings into the chapter polish prompt
- `enable_scrubbing` has no effect if `enable_final_edit` skips Phase 9 entirely

## Developer Guide

### `prose-scrubber`

`prose-scrubber` is not a standalone orchestrator phase, but its prompt is now wired into `src/presentation/agents/final_editor.py` as Stage 1a of the final-edit flow.

The active runtime does not write a separate `chapter_{N}_scrubbed` artifact. The findings stay in-memory and flow into the Stage 2 chapter-polish prompt.

### `final-editor`

`final-editor` is implemented in `src/presentation/agents/final_editor.py` and called directly from Phase 9 of `src/presentation/orchestrator.py`.

Operational details:

- When `settings.enable_scrubbing` is `true`, loads `prompts/final_edit/prose_scrub.md` and gathers `prose_findings`
- When `settings.enable_scrubbing` is `true`, loads `prompts/final_edit/voice_consistency_pass.md` and gathers `voice_findings`
- Loads `prompts/final_edit/edit_chapter_direct.md` via `PromptLoader.load_prompt()`
- Injects `{prose_findings}` and `{voice_findings}` into `edit_chapter_direct.md`
- Uses the `chapter_writer` model role for the streaming edit pass
- Emits one `WikiContextEvent` per chapter with phase `final-edit`
- Sends one user message containing the chapter title and full chapter content
- Replaces each chapter with streamed output when non-empty; otherwise preserves the original text
- Returns `FinalEditResult` with `edited_chapters`, `chapters_processed`, `total_issues_found`, and `total_revisions_made`
- Writes `stories/<story>/output/story_edited.md` from the edited chapters when at least one edited chapter has non-empty content
- Persists `final_edit_complete` after the phase finishes

`final-editor` now runs before assembly, not after it. `story.md` is assembled from the already-edited `state.approved_chapters`, so `story_edited.md` and `story.md` are aligned unless later phases mutate chapter content again.

### Tool Usage

| Agent | Tool | Purpose |
|-------|------|---------|
| `final-editor` | `PromptLoader` | Load `prompts/final_edit/prose_scrub.md` and `prompts/final_edit/voice_consistency_pass.md` when scrubbing is enabled |
| `final-editor` | `PromptLoader` | Load `prompts/final_edit/edit_chapter_direct.md` |
| `final-editor` | `ModelProvider.stream_text(...)` | Run one streamed edit pass per approved chapter |
| `final-editor` | `TokenStreamBus` | Surface editing output tokens live |
| `final-editor` | `WikiContextBus` | Emit one phase event per chapter |

### Constraints

The current implementation relies on agent prompt instructions rather than a separate runtime skill loader. The active guardrails are:

- Final-edit is optional and skips cleanly when disabled
- Scrubbing diagnostics are optional and skip cleanly when disabled, passing empty findings into Stage 2
- Empty model output must not erase accepted chapter content
- The phase edits accepted chapter drafts only; it does not reopen approval gates
- The current orchestrator writes one phase-level savepoint, not per-chapter final-edit checkpoints

### Key Files

- `prompts/final_edit/prose_scrub.md` — Stage 1a prose diagnostics prompt
- `prompts/final_edit/voice_consistency_pass.md` — Stage 1b voice diagnostics prompt
- `prompts/final_edit/edit_chapter_direct.md` — Stage 2 direct-generation prompt for manuscript polish with injected diagnostic findings
- `prompts/agents/final-editor.md` — OpenCode/Copilot workflow specification (not used by the Python-native runtime)
- `src/presentation/agents/final_editor.py` — streaming agent implementation and empty-output fallback
- `src/presentation/orchestrator.py` — Phase 9 wiring, config flag check, `story_edited.md` write, and `final_edit_complete` savepoint
- `src/application/pipeline/handoffs.py` — `FinalEditResult` dataclass consumed by the orchestrator

### Data

The current Python-native path mutates `state.approved_chapters`, writes one edited manuscript artifact, and adds one completion savepoint. It does not add new wiki entities or alter wiki facts.

| Artifact | Producer | Notes |
|----------|----------|-------|
| `stories/<story>/output/story_edited.md` | `final-editor` phase controller | Edited manuscript assembled from `FinalEditResult.edited_chapters` |
| `final_edit_complete` | `final-editor` phase controller | Phase 9 completion savepoint |

### Testing

`tests/unit/test_final_editor_agent.py`, `tests/unit/test_final_editor.py`, and `tests/unit/test_orchestrator.py` cover the active final-edit flow, including scrub gating, prompt-variable handoff, and Phase 9 orchestration.

- `prompts/final_edit/edit_chapter_direct.md`
- `src/presentation/agents/final_editor.py`
- `src/presentation/orchestrator.py`

## Configuration

| Setting | Location | Default | Effect |
|---------|----------|---------|--------|
| `enable_scrubbing` | `generation` | `true` | When final-edit runs, execute prose-scrub and voice-consistency diagnostics before chapter polish |
| `enable_final_edit` | `generation` | `true` when the raw config key is absent in `orchestrator.py` | Enables or skips Phase 9 `final-editor` |

## Related

- [Story Orchestrator](./story-orchestrator.md) — Pipeline placement, subagent registry, and savepoint flow
- [Story Planner](./story-planner.md) — Adjacent narrative quality pass that now runs before characters
- [ADR 001: Hybrid Agent-Tool Architecture](../planning/adr/001-hybrid-agent-tool-architecture.md) — Depth-1 orchestration pattern
- Issue #185 — Implement final-edit phase and add narrative-arc phase
- PR #198 — Narrative-arc and final-edit implementation
- Issue #295 — Final-editor scrub and voice diagnostics
- PR #307 — Wire `enable_scrubbing` into `FinalEditorAgent`