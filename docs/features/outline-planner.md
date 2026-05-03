# Outline Planner

> Phase 3 outline-generation agent with direct, per-chapter expansion, and chunked-window modes.

## Overview

`OutlinePlannerAgent` lives in `src/presentation/agents/outline_planner.py` and runs during the orchestrator's outline phase. It receives the story prompt plus the `base_context` and `story_elements` extracted by `StoryFoundationAgent`, then returns an `OutlineResult` that later phases and the approval gate consume.

The agent now has three generation modes. The mode is selected entirely from `GenerationSettings`: `expand_outline` decides whether the runtime stays in the legacy one-call path or enters the structured outline pipeline, and `use_chunked_outline_generation` further switches long outlines from per-chapter expansion to chunk windows with explicit continuity analysis.

## Generation Modes

| Mode | Activation | Prompt flow | Persisted artefacts |
|---|---|---|---|
| Direct | `expand_outline: false` | `prompts/outline/create_direct.md` | No outline-phase markdown files are written; the returned outline lives in `OutlineResult.summary` and `chapter_outlines` |
| Expanded | `expand_outline: true` and either `use_chunked_outline_generation: false` or `wanted_chapters <= outline_chunk_size` | `create_skeleton` → per-chapter `expand_chapter_detail` → `strip_elements` | `stories/<story>/outline/skeleton.md` and `stories/<story>/outline/details/chapter_{N}.md` |
| Chunked | `expand_outline: true`, `use_chunked_outline_generation: true`, and `wanted_chapters > outline_chunk_size` | Windowed `create_chunk` calls → between-window `analyze_continuity` → final `analyze_enrichment` | `stories/<story>/outline/chunks/chunk_{start}_{end}.md`, `stories/<story>/outline/continuity/continuity_{start}_{end}.md`, and `stories/<story>/outline/enrichment.md` |

Chunked mode is the new path added for issue #302 / PR #314. It keeps each outline call bounded to one chapter window while still carrying forward previous windows and the latest continuity findings.

## User Guide

Enable chunked generation when you want a detailed outline, expect the story to exceed one chunk window, and need tighter continuity between adjacent sections of the outline. With the current defaults, that means leaving `expand_outline: true`, setting `use_chunked_outline_generation: true`, and requesting more than `outline_chunk_size` chapters.

Chunked mode runs this loop:

1. Split the outline into chapter windows of `outline_chunk_size` chapters.
2. Generate each window with `prompts/outline/create_chunk.md`, feeding prior windows back in as context.
3. Before the next window, run `prompts/outline/analyze_continuity.md` and emit the findings on the token bus.
4. After the last window, run `prompts/outline/analyze_enrichment.md` and store its output in `OutlineResult.enrichment_suggestions`.

If the story is short enough to fit inside one window, the runtime does not force the chunked branch. It stays on the existing expanded path, which still produces `chapter_skeletons`, per-chapter detail files, and stripped enrichment notes.

## Developer Guide

### Key Files

- `src/presentation/agents/outline_planner.py` — mode selection, prompt loading, artefact persistence, and `OutlineResult` assembly
- `src/domain/value_objects/generation_settings.py` — `expand_outline`, `use_chunked_outline_generation`, and `outline_chunk_size` defaults and validation
- `prompts/outline/create_direct.md` — single-call direct outline prompt
- `prompts/outline/create_skeleton.md` — expanded-path skeleton prompt
- `prompts/outline/expand_chapter_detail.md` — expanded-path per-chapter detail prompt
- `prompts/outline/strip_elements.md` — expanded-path cleanup and enrichment prompt
- `prompts/outline/create_chunk.md` — chunked-path window generator
- `prompts/outline/analyze_continuity.md` — adjacent-window continuity checker
- `prompts/outline/analyze_enrichment.md` — final enrichment-analysis prompt

### Returned Data

All three paths return an `OutlineResult`, but the populated fields differ by mode:

| Field | Direct | Expanded | Chunked |
|---|---|---|---|
| `summary` | Full outline text from `create_direct` | Skeleton text from `create_skeleton` | Concatenated chunk text |
| `chapter_outlines` | Parsed from direct output | Parsed from skeleton output | Parsed from concatenated chunk output |
| `chapter_skeletons` | Empty | Populated | Empty |
| `chapter_details` | Empty | Populated from `outline/details/` | Empty |
| `enrichment_suggestions` | Empty | Output from `strip_elements` | Output from `analyze_enrichment` |

Chunked mode also emits a token-bus section after each continuity pass so the TUI and headless logs surface the current mismatch analysis before the next window starts.

When the orchestrator persists the returned `OutlineResult`, it externalizes each `chapter_outlines[].summary` value to `stories/<story>/outline/chapter_<N>_summary.md` and replaces the inline text in `pipeline_state.json` with `{"$ref": ...}`. If `enrichment_suggestions` contains a fenced JSON string, the orchestrator strips the fence, parses the JSON, writes `stories/<story>/outline/enrichment_suggestions.json`, and stores `{"$ref": "outline/enrichment_suggestions.json"}` in the savepoint. `_build_story_elements()` resolves those summary pointers before serializing chapter outlines back into later prompt payloads.

## Configuration

| Setting | Default | Effect |
|---|---|---|
| `expand_outline` | `true` | Enables the structured outline pipeline; when `false`, the agent always uses direct mode |
| `use_chunked_outline_generation` | `false` | Allows the chunked branch, but only when `wanted_chapters > outline_chunk_size` |
| `outline_chunk_size` | `4` | Maximum number of chapters per chunk window |
| `wanted_chapters` | `40` | Requested outline length; compared against `outline_chunk_size` to decide whether chunking activates |

## Testing

The behavior is covered by focused unit tests:

- `tests/unit/test_outline_planner_agent.py` — direct and expanded mode coverage
- `tests/unit/test_outline_chunked.py` — chunk-window generation, continuity passes, and enrichment output
- `tests/unit/test_outline_planner_parser.py` — chapter-outline parsing behavior shared by all three modes

## Related

- [Story Orchestrator](./story-orchestrator.md)
- [Direct-Generation Prompts](./direct-generation-prompts.md)
- [Comprehensive Manual](../manual.md)
- Issue #302 — Chunked outline generation with continuity checks between windows
- PR #314 — Outline planner chunked path
