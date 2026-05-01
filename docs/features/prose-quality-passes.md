# Prose Quality Passes

> Conditional prose-polish layers for chapter cleanup and late-stage manuscript editing.

## Overview

Issue #121 and PR #128 introduced two prose-quality surfaces: `prose-scrubber` and `final-editor`. The current Python-native orchestrator slice only wires `final-editor`. Issue #185 / PR #198 replaces the old Phase 9 stub with a real `FinalEditorAgent` execution path in `src/presentation/orchestrator.py`.

`final-editor` now runs after the chapter loop and before assembly. It sends one approved chapter at a time through a streamed LLM edit pass, preserves the original chapter if the model returns empty output, updates `state.approved_chapters`, and writes `stories/<name>/output/story_edited.md` before `story.md` is assembled.

`prose-scrubber` prompt assets still exist, but that phase is not currently invoked by `src/presentation/orchestrator.py`. Both passes remain optional at the configuration layer, and neither replaces the chapter approval gate.

## Pipeline Placement

| Pass | Agent | Pipeline Position | Trigger | Scope |
|------|-------|-------------------|---------|-------|
| Prose Scrub | `prose-scrubber` | Not wired in current orchestrator slice | `generation.enable_scrubbing: true` | Sentence and paragraph |
| Final Edit | `final-editor` | Phase 9, after chapter-loop and before assembly | `generation.enable_final_edit` not explicitly `false` | One accepted chapter at a time |

The passes are complementary:

- `quality-reviewer` is still a separate concept from prose polishing.
- `prose-scrubber` remains a documented prompt surface, not an active orchestrator phase.
- `final-editor` is the only prose-quality pass currently executed by the Python-native orchestrator.

## User Guide

Enable or disable the passes in the `generation` config block.

```yaml
generation:
  enable_scrubbing: true
  enable_final_edit: true
```

Current behavior in `src/presentation/orchestrator.py`:

- `enable_final_edit` skips Phase 9 only when the value is explicitly `false`
- if the key is missing from the raw `generation` config mapping, the orchestrator treats final-edit as enabled
- `enable_scrubbing` is not currently consulted by the active orchestrator code path

## Developer Guide

### `prose-scrubber`

`prose-scrubber` is not wired into `src/presentation/orchestrator.py` today. Keep its prompt assets and related docs as design/reference material until a future pipeline slice reconnects the phase.

Because the active orchestrator never calls this pass, do not document `chapter_{N}_scrubbed` as a current runtime artifact of the Python-native path.

### `final-editor`

`final-editor` is implemented in `src/presentation/agents/final_editor.py` and called directly from Phase 9 of `src/presentation/orchestrator.py`.

Operational details:

- Loads `prompts/final_edit/edit_chapter_direct.md` via `PromptLoader.load_prompt()`
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
| `final-editor` | `PromptLoader` | Load `prompts/final_edit/edit_chapter_direct.md` |
| `final-editor` | `ModelProvider.stream_text(...)` | Run one streamed edit pass per approved chapter |
| `final-editor` | `TokenStreamBus` | Surface editing output tokens live |
| `final-editor` | `WikiContextBus` | Emit one phase event per chapter |

### Constraints

The current implementation relies on agent prompt instructions rather than a separate runtime skill loader. The active guardrails are:

- Final-edit is optional and skips cleanly when disabled
- Empty model output must not erase accepted chapter content
- The phase edits accepted chapter drafts only; it does not reopen approval gates
- The current orchestrator writes one phase-level savepoint, not per-chapter final-edit checkpoints

### Key Files

- `prompts/final_edit/edit_chapter_direct.md` — Phase 9 direct-generation prompt for manuscript polish
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

`tests/unit/test_orchestrator.py` covers the active final-edit orchestration paths with `test_final_edit_phase_invokes_agent()` and `test_final_edit_phase_skipped_when_disabled()`.

- `prompts/final_edit/edit_chapter_direct.md`
- `src/presentation/agents/final_editor.py`
- `src/presentation/orchestrator.py`

## Configuration

| Setting | Location | Default | Effect |
|---------|----------|---------|--------|
| `enable_scrubbing` | `generation` | `true` | Reserved for a future prose-scrubber reintegration; unused by the active orchestrator |
| `enable_final_edit` | `generation` | `true` when the raw config key is absent in `orchestrator.py` | Enables or skips Phase 9 `final-editor` |

## Related

- [Story Orchestrator](./story-orchestrator.md) — Pipeline placement, subagent registry, and savepoint flow
- [Story Planner](./story-planner.md) — Adjacent narrative quality pass that now runs before characters
- [ADR 001: Hybrid Agent-Tool Architecture](../planning/adr/001-hybrid-agent-tool-architecture.md) — Depth-1 orchestration pattern
- Issue #185 — Implement final-edit phase and add narrative-arc phase
- PR #198 — Narrative-arc and final-edit implementation