# Prose Quality Passes

> Conditional prose-polish layers for chapter cleanup and post-assembly manuscript editing.

## Overview

Issue #121 and PR #128 added two distinct prose-quality subagents to the story pipeline: `prose-scrubber` and `final-editor`. They improve prose quality at different points in the pipeline and at different scopes.

`prose-scrubber` runs inside the per-chapter loop after Phase 7f has accepted a chapter. It targets sentence and paragraph-level defects such as adverb overuse, filter words, repetitive phrasing, and show-vs-tell drift. `final-editor` runs after Phase 8 assembly and revisits each assembled chapter for voice consistency, pacing, and cross-chapter coherence.

Both passes are optional, controlled by config flags, and constrained to surgical prose edits. They do not replace the chapter-quality gate handled by `quality-reviewer`, and they must not change plot events, world facts, or entity state.

## Pipeline Placement

| Pass | Agent | Pipeline Position | Trigger | Scope |
|------|-------|-------------------|---------|-------|
| Prose Scrub | `prose-scrubber` | Phase 7.5, after Phase 7f | `generation.enable_scrubbing: true` | Sentence and paragraph |
| Final Edit | `final-editor` | Phase 9, after Phase 8 assembly | `generation.enable_final_edit: true` | Chapter-level prose in manuscript context |

The passes are complementary:

- `quality-reviewer` decides whether a chapter is good enough to accept.
- `prose-scrubber` cleans local prose issues in the accepted chapter text.
- `final-editor` performs a later manuscript-context pass for style, pacing, and cross-chapter continuity of voice.

## User Guide

Enable or disable the passes in `config.md` under `generation`.

```yaml
generation:
  enable_scrubbing: true
  enable_final_edit: false

models:
  scrub_model: your-fast-analysis-model
```

When `enable_scrubbing` is true, the orchestrator dispatches `prose-scrubber` after the chapter quality loop finishes. When `enable_final_edit` is true, the orchestrator dispatches `final-editor` after manuscript assembly. If a flag is false, the corresponding pass is skipped cleanly.

## Developer Guide

### `prose-scrubber`

`prose-scrubber` reads one chapter from story state, analyzes it with the `final_edit/prose_scrub` prompt, and applies targeted `scene-writer` revisions.

It focuses on four issue types:

- Adverb overuse
- Filter words and distancing constructions
- Repetitive phrase patterns
- Show-vs-tell imbalance

Operational details:

- Uses `config.models.scrub_model` when present; otherwise uses the default model role
- Stops after at most five revision calls for one chapter
- Writes the revised chapter object back to the original text-bearing field in story state
- Creates `chapter_{N}_scrubbed` savepoints
- Returns issue and revision counts to the orchestrator

Because this pass is prose-only, it does not re-run wiki updates, recap generation, or wiki lint.

### `final-editor`

`final-editor` runs after the story has been assembled. It processes chapters one by one, but it evaluates them in manuscript context by pulling prior-chapter material through `rag-query`.

It performs two analysis passes per chapter:

1. `final_edit/voice_consistency_pass` for voice consistency, pacing, and cross-chapter coherence
2. `final_edit/prose_scrub` for a second sentence-level cleanup on the assembled chapter text

Operational details:

- Reads chapter text from story state and preserves sibling fields when writing updates back
- Uses `rag-query` to gather prior chapter context for stylistic continuity
- Applies up to three targeted revisions from the voice-analysis pass and up to three targeted revisions from the scrub pass
- Creates `chapter_{N}_final_edited` savepoints per chapter
- Creates `final_edit_complete` when the full manuscript pass finishes

`final-editor` runs after assembly, not instead of `quality-reviewer`. It assumes each chapter has already passed the acceptance gate and only polishes the accepted text.

### Tool Usage

| Agent | Tool | Purpose |
|-------|------|---------|
| `prose-scrubber` | `story-state` | Read and write chapter objects |
| `prose-scrubber` | `scene-writer` | Apply local prose revisions |
| `prose-scrubber` | `prompt-loader` | Load `final_edit/prose_scrub` |
| `prose-scrubber` | `savepoint-mgr` | Record `chapter_{N}_scrubbed` |
| `final-editor` | `story-state` | Read and write assembled chapter objects |
| `final-editor` | `scene-writer` | Apply voice, pacing, and scrub revisions |
| `final-editor` | `rag-query` | Retrieve prior-chapter context |
| `final-editor` | `prompt-loader` | Load `final_edit/voice_consistency_pass` and `final_edit/prose_scrub` |
| `final-editor` | `savepoint-mgr` | Record per-chapter and final completion savepoints |

### Constraints

Both agents load `.opencode/skills/final-edit/SKILL.md` and inherit the same hard limits:

- Allowed scope: sentence, paragraph, and local chapter-level prose revision
- Forbidden: new plot events, removed plot events, changed entity facts, changed timeline facts, changed world rules
- Forbidden: wholesale chapter rewrites or full chapter replacement
- Required fallback: mark `needs_review` when a problem exceeds prose scope instead of forcing a rewrite
- Architecture rule: depth-1 nesting only; both agents are tool-only subagents

### Key Files

- `.opencode/agents/prose-scrubber.md` — Phase 7.5 chapter scrub workflow
- `.opencode/agents/final-editor.md` — Phase 9 manuscript polish workflow
- `.opencode/skills/final-edit/SKILL.md` — shared constraints, pass types, revision budget, status tokens
- `prompts/final_edit/prose_scrub.md` — sentence and paragraph-level issue extraction prompt
- `prompts/final_edit/voice_consistency_pass.md` — voice, pacing, and cross-chapter coherence prompt
- `.opencode/agents/story-orchestrator.md` — orchestrator integration points and feature flags

### Data

The passes mutate chapter text in story state and add savepoints. They do not add new wiki entities or alter wiki facts.

| Artifact | Producer | Notes |
|----------|----------|-------|
| `chapter_{N}_scrubbed` | `prose-scrubber` | Per-chapter Phase 7.5 checkpoint |
| `chapter_{N}_final_edited` | `final-editor` | Per-chapter post-assembly checkpoint |
| `final_edit_complete` | `final-editor` | Final manuscript-polish checkpoint |

### Testing

PR #128 updated the prompt relocation unit test to account for the new prompt files. For documentation changes, verify the feature descriptions against the source agent files and prompt templates:

- `.opencode/agents/prose-scrubber.md`
- `.opencode/agents/final-editor.md`
- `.opencode/skills/final-edit/SKILL.md`
- `prompts/final_edit/prose_scrub.md`
- `prompts/final_edit/voice_consistency_pass.md`

## Configuration

| Setting | Location | Default | Effect |
|---------|----------|---------|--------|
| `enable_scrubbing` | `generation` | `true` | Enables Phase 7.5 `prose-scrubber` |
| `enable_final_edit` | `generation` | `false` | Enables Phase 9 `final-editor` |
| `scrub_model` | `models` | unset | Optional named model role used by `prose-scrubber` |

## Related

- [Story Orchestrator](./story-orchestrator.md) — Pipeline placement, subagent registry, and savepoint flow
- [Tools Reference](../tools.md) — Deterministic tool contracts used by both subagents
- [ADR 001: Hybrid Agent-Tool Architecture](../planning/adr/001-hybrid-agent-tool-architecture.md) — Depth-1 orchestration pattern
- Issue #121 — Initial implementation request
- PR #128 — Implemented `final-editor`, `prose-scrubber`, shared skill, and prompt templates