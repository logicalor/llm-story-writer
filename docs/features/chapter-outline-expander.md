# Chapter Outline Expander

> Dedicated Phase 7a subagent that expands chapter synopses, decomposes them into scene definitions, and carries structured continuity forward between chapters.

## Overview

Issue #123 and PR #129 moved the Phase 7a chapter outline expansion loop out of the story orchestrator and into a dedicated `chapter-outline-expander` subagent. Issue #154 and PR #155 extended that subagent so Phase 7a now performs two distinct jobs for each chapter: it first produces an expanded chapter synopsis, then optionally decomposes that synopsis into a bounded list of scene objects before chapter drafting starts.

This change fixes the earlier one-scene-per-chapter failure mode. Before PR #155, Phase 7a produced a single expanded synopsis paragraph and Phase 7b `parse-definitions` often turned that synopsis into a single scene. The new flow generates scene definitions directly from the synopsis using the `outline-generator expand-to-scenes` operation, so downstream scene writing starts from explicit multi-scene structure rather than a reformatted synopsis blob.

## Pipeline Placement

`chapter-outline-expander` runs in Phase 7a of the story pipeline.

| Step | Runs When | What It Produces |
|------|-----------|------------------|
| Phase 7a | Once per story, before any chapter drafting | `chapters.{N}.expanded_outline`, `chapter_{N}/scene_definitions`, and chapter-outline expansion savepoints |
| Phase 7g dependency | After each accepted chapter, on later iterations | Consumes `chapters.{N-1}.handoff` to enrich continuity for the next expansion |

Operationally, the orchestrator dispatches one bounded Phase 7a subagent, waits for expansion to complete, then starts the normal per-chapter drafting flow. Phase 7a no longer stops at a synopsis-only artifact when scene expansion is enabled.

## Phase 7a Workflow

For each chapter, the subagent performs these steps in order:

1. Call `outline-generator` with `operation: "expand-chapter"` to create the chapter synopsis and next-step continuity analysis. The tool writes the result to the `expanded_chapter_{N}_{N}` savepoint.
2. When `generation.scene_expansion_enabled` is `true`, call `outline-generator` again with `operation: "expand-to-scenes"` to convert the synopsis into a JSON array of scene objects. The tool writes `chapter_{N}/scene_definitions`.

The second call is the feature added in PR #155. It uses `prompts/chapters/expand_to_scenes.md`, enforces the requested scene count band, and writes `chapter_{N}/scene_definitions` directly during Phase 7a.

## Configuration

Scene decomposition is controlled by three `generation:` settings:

| Key | Default | Meaning |
|-----|---------|---------|
| `scene_expansion_enabled` | `true` | Enables the new Phase 7a scene-decomposition pass |
| `scenes_per_chapter_min` | `8` | Lower bound for generated scene count |
| `scenes_per_chapter_max` | `16` | Upper bound for generated scene count |

`GenerationSettings` validates the count band with `1 <= scenes_per_chapter_min <= scenes_per_chapter_max <= 30`. This keeps the agent contract aligned with the tool-level validation in `outline-generator`.

When `scene_expansion_enabled` is `false`, the pipeline reverts to the legacy synopsis-only Phase 7a behavior. Phase 7b then parses the chapter outline itself, which restores the pre-#154 one-scene-per-chapter path.

## Inputs And Outputs

### Inputs

The orchestrator dispatches the subagent with a compact contract:

- `story_name` — story state namespace to read and write
- `wanted_chapters` — total number of chapters to expand
- `expand_outline` — skip flag for installations that disable expansion
- `model` — optional model override for `outline-generator`

During the loop, the subagent also reads:

- `chapters.{N-1}.handoff` from story state when a prior chapter handoff exists
- The previous `continuitySummary` returned by `outline-generator`
- `chapters.{N-1}.recap` when scene expansion is enabled and prior recap context exists

### Outputs

For each chapter, the tool writes (no agent-side savepoint calls required):

- `expanded_chapter_{N}_{N}` savepoint — expanded chapter outline used by later drafting phases (single source of truth)
- `chapter_{N}/scene_definitions` savepoint — structured scene objects written by `expand-to-scenes` when scene expansion is enabled
- `expansion_continuity_{N}_{N}` savepoint — per-chapter continuity analysis

At completion the tool auto-writes the `outlines_expanded` milestone savepoint, and the subagent returns a small status object to the orchestrator, such as `complete` or `skipped`.

## Backwards Compatibility And Resume Behavior

Phase 7b still uses `scene-writer` with `operation: "parse-definitions"`. That path remains intact for compatibility, but it now benefits from existing resume logic: if `chapter_{N}/scene_definitions` already exists because Phase 7a wrote it, `parse-definitions` returns the saved definitions immediately instead of regenerating them.

This keeps the downstream chapter-writing contract stable. Existing code still reads the same `chapter_{N}/scene_definitions` savepoint; PR #155 changes only when and how that savepoint is populated.

## Handoff Artifact Relationship

The per-chapter handoff artifact is the developer-facing reason this subagent matters. After each accepted chapter, the orchestrator delegates `chapters.{N}.handoff` generation to `story-assembler` with `operation: "generate-handoff"`. That tool reads the accepted chapter's expansion context from story state, renders `prompts/chapters/generate_handoff.md`, and writes the structured JSON artifact back to `state.json`.

That artifact contains five continuity categories:

- `resolved_beats`
- `obligations`
- `active_tensions`
- `timeline`
- `character_deltas`

On the next expansion iteration, `chapter-outline-expander` reads that structured state and prepends it to the continuity input sent to `outline-generator`. Operators should expect later chapter expansions to reflect explicit carry-forward obligations and character-state changes, not only a free-form rolling summary.

## Operator Notes

- If `generation.expand_outline` is `false`, the subagent exits immediately and the pipeline proceeds without expanded outlines.
- If `generation.scene_expansion_enabled` is `true`, Phase 7a writes scene definitions before chapter drafting begins.
- If `generation.scene_expansion_enabled` is `false`, Phase 7a skips scene decomposition and the system falls back to the legacy Phase 7b parse step.
- This agent is depth-1 only. It calls tools and never dispatches nested subagents.
- Continuity state now survives orchestrator context pressure better because the orchestrator no longer owns the rolling Phase 7a loop.
- The handoff artifact lives in story state, not the wiki. It is continuity-planning data for expansion, not reader-facing story memory.

## Key Files

| File | Purpose |
|------|---------|
| `prompts/agents/chapter-outline-expander.md` | Subagent workflow, tool contract, continuity threading rules |
| `prompts/agents/story-orchestrator.md` | Parent orchestration logic for Phase 7a dispatch and Phase 7g handoff delegation |
| `prompts/chapters/expand_to_scenes.md` | Prompt template for synopsis-to-scene decomposition |
| `prompts/chapters/generate_handoff.md` | Prompt template for the structured handoff JSON artifact |
| `src/domain/value_objects/generation_settings.py` | Phase 7a scene-expansion flags and scene-count band validation |
| `prompts/skills/story-pipeline/SKILL.md` | Pipeline reference updated with the new Phase 7a subagent |

## Related

- [Story Orchestrator](./story-orchestrator.md) — parent pipeline and per-chapter loop placement
- [Tools Reference](../tools.md) — deterministic tools used by the subagent and orchestrator
- [ADR 001: Hybrid Agent-Tool Architecture](../planning/adr/001-hybrid-agent-tool-architecture.md) — depth-1 delegation rule
- Issue #154 — request to replace synopsis-only expansion with bounded scene decomposition
- PR #155 — implementation of `outline-generator expand-to-scenes` and Phase 7a scene savepoints
- Issue #123 — implementation request for Phase 7a extraction and handoff artifact
- PR #129 — implementation of `chapter-outline-expander` and chapter handoff storage
