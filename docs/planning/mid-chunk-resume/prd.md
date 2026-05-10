# PRD: Mid-Chunk Resume for Outline and Scene Generation

> Teach the pipeline to resume chunked outline generation and scene generation from the first incomplete item, not from the beginning.

**Date:** 2026-05-10
**Author:** Planner agent
**Status:** Draft

---

## Problem Statement

Two pipeline phases generate content in loops over multiple LLM calls, each call producing an independently persisted savepoint. When a run is interrupted mid-loop, the individual savepoints written so far are preserved on disk — but the driving agent has no mechanism to detect which items are already complete. On resume it restarts the loop from item 1.

### Chunked outline generation (outline-planner Phase 3)

`outline-planner` loops over chapter ranges in chunks of `outline_chunk_size` (default 10). Each call to `outline-generator expand-chapter` writes an `outline_chunk_{start}_{end}` savepoint and a `continuity_{start}_{end}` savepoint. If the run is interrupted after chunk 2 of 6, both of those savepoints exist. On resume:

1. The orchestrator detects `outline_complete` is missing and re-dispatches `outline-planner`.
2. `outline-planner` starts its chunk loop from chunk 1.
3. For chunks 1 and 2, `expand-chapter` checks the savepoint and returns immediately (no LLM call). But the agent still issues those tool calls and waits for each response.
4. For chunks 3–6 it generates normally.
5. The agent accumulates `chunk_outline` strings in context and builds `merged_outline` at the end.

This is **functionally correct** — the cached tool calls short-circuit — but the agent always re-iterates from chunk 1 regardless. For a 30-chapter story with chunk_size 5 interrupted at chunk 5 of 6, the agent still makes five wasteful tool calls before it reaches real work. Worse: the agent LLM could in principle fail to faithfully replay the continuity threading from cached responses, producing a corrupt `merged_outline` for the uncompleted chunk.

The user-facing symptom: "it resumes from the beginning."

### Chapter outline expansion (chapter-outline-expander Phase 7a)

`chapter-outline-expander` loops chapter-by-chapter, calling `expand-chapter` with `phase="chapter"` for each chapter N. Each call writes `expanded_chapter_{N}_{N}`. On resume the subagent is re-dispatched and starts from chapter 1, re-issuing `expand-chapter` (and, when enabled, `expand-to-scenes`) for each completed chapter before reaching the first incomplete one. The tool auto-loads continuity from the previous chapter's savepoint, so correctness is not compromised — but the wasted tool calls scale linearly with completed chapters.

### Scene generation (chapter-writer Phase 7b)

`chapter-writer` is dispatched per-chapter. Its scene loop calls `wiki-snapshot` then `scene-writer generate` for each scene. `scene-writer generate` checks `chapter_{N}/scene_{M}` and returns cached if complete. But `wiki-snapshot` — which runs a three-stage retrieval pipeline (entity match → metadata query → semantic search) — is called unconditionally before each `scene-writer generate`, even for scenes whose prose is already on disk. On resume the agent re-issues `wiki-snapshot` for every completed scene before reaching the first incomplete one.

The chapter-writer prompt already contains a vague "Resuming from a savepoint" note, but it does not give the agent a concrete procedure for identifying the first incomplete scene and skipping context assembly for earlier ones.

---

## Goals

1. **Skip completed chunks.** When `outline-planner` resumes its chunk loop, it should not issue `expand-chapter` tool calls for chunks whose `outline_chunk_{start}_{end}` savepoint already exists. It should load those directly and start real work at the first missing chunk.
2. **Skip completed chapter expansions.** When `chapter-outline-expander` resumes its per-chapter loop, it should start at the first chapter N whose `expanded_chapter_{N}_{N}` savepoint is missing.
3. **Skip completed scenes.** When `chapter-writer` resumes its scene loop, it should find the first missing `chapter_{N}/scene_{M}` savepoint and start there, skipping `wiki-snapshot` for scenes whose prose is already persisted.
4. **Preserve correctness.** The continuity threading for the first re-started chunk/chapter must be seeded correctly from the last completed item's savepoint.
5. **Agent prompt changes only.** The underlying tool implementations are already idempotent and correct. No Python changes are required.

---

## Non-Goals

- **Tracking progress within a single LLM call.** If a single `expand-chapter` call is interrupted, that call is lost. Granularity is one tool call.
- **Parallelising the resume scan.** The agent calls `savepoint-mgr list` once and filters in context. No new tool operations are required.
- **Cross-run branching or time-travel.** There is one head per story.
- **Changing the savepoint naming scheme.** Existing savepoint names are stable and not renamed.
- **Python tool changes.** All fixes are agent prompt rewrites.

---

## User Stories

### Story author

- As a user whose run was interrupted after 4 of 6 outline chunks, I want the pipeline to generate only chunks 5–6 on resume, not repeat chunks 1–4.
- As a user whose chapter run was killed after scene 6 of 12, I want the pipeline to continue from scene 7, not re-assemble context for scenes 1–6.
- As a user, I want the outline and scene resume behaviour to be consistent across runs, not dependent on whether the LLM happens to check the right savepoints in context.

### Contributor

- As a contributor, I want the resume logic for chunked loops to follow an explicit, tested procedure in the agent prompt, not rely on the LLM's ad-hoc initiative.

---

## Root Cause Analysis

All three gaps share the same pattern: the agent prompt instructs the agent to loop from item 1 without first determining which items are already persisted. The individual tool calls are idempotent, so no LLM work is duplicated — but the agent still issues O(completed\_items) tool calls before reaching the first real unit of work.

The continuity risk is also real for chunked outline generation: the `continuitySummary` for the first uncompleted chunk must be taken from the last completed chunk's `continuity_{start}_{end}` savepoint. If the agent re-collects it from cached `expand-chapter` responses this works, but it depends on the LLM reliably replaying the threaded context across all prior cached calls. Loading the savepoint directly is safer and more explicit.

---

## Proposed Solution

Three targeted agent prompt rewrites, one per affected loop. Each follows the same pattern:

### Pre-loop scan

At the start of each loop, the agent calls `savepoint-mgr list` (which returns all savepoint names for the story) and filters in context for the relevant namespace:

- Chunked outline: `outline_chunk_{start}_{end}` entries
- Chapter expansion: `expanded_chapter_{N}_{N}` entries
- Scene generation: `chapter_{N}/scene_{M}` entries

From this list the agent determines the **first incomplete item** and the **last complete item** (for continuity seeding).

### Skip-and-seed

For already-complete items, the agent does not call the generation tool. Instead it:

1. Loads the chunk/chapter/scene content directly from its savepoint via `savepoint-mgr load` (for items whose content feeds into the accumulation, e.g. `chunk_outline` in merged outline building, or whose `continuity_*` savepoint is needed as the seed for the next call).
2. Records that item as done and advances the loop counter.

For the continuity seed:
- Chunked outline: load `continuity_{last_complete_end}_{last_complete_end}` via `savepoint-mgr load`.
- Chapter expansion: continuity is auto-loaded by the tool (no agent action required).
- Scenes: no continuity threading; `previous_scene` is auto-loaded by `scene-writer generate` from the prior scene's savepoint.

### Start generation at the first incomplete item

The agent begins issuing generation tool calls only from the first missing item. Normal loop logic continues from there.

### Implementation scope

All changes are to these three files in `prompts/agents/`:

| File | Section changed |
|------|----------------|
| `outline-planner.md` | Phase 3 — Outline Generation (chunked path) |
| `chapter-outline-expander.md` | Workflow Step 4 (the chapter loop) |
| `chapter-writer.md` | Scene Generation Loop |

No Python files change. No new savepoint keys. No new tool operations.

---

## Acceptance Criteria

- [ ] `outline-planner` Phase 3 (chunked path) explicitly instructs: call `savepoint-mgr list`, identify complete chunks, load their `chunk_outline` from savepoints, load the last `continuity_*` savepoint as the seed, and begin `expand-chapter` calls from the first missing chunk.
- [ ] `chapter-outline-expander` Workflow Step 4 explicitly instructs: call `savepoint-mgr list`, identify complete chapters via `expanded_chapter_{N}_{N}` savepoints, and start the loop from the first N without that savepoint.
- [ ] `chapter-writer` Scene Generation Loop explicitly instructs: call `savepoint-mgr list` and filter for `chapter_{N}/scene_{M}` entries, determine the first incomplete scene, skip `wiki-snapshot` and `scene-writer generate` for complete scenes, and begin the loop from the first incomplete scene.
- [ ] The continuity seed for the first re-started outline chunk is explicitly loaded from the last complete `continuity_{start}_{end}` savepoint, not from a re-played `expand-chapter` response.
- [ ] All three prompt sections are tested: unit tests simulate a partial-completion scenario (some savepoints pre-written) and verify the agent would skip completed items and start from the correct position.

---

## Open Questions

None — the fix scope is well-defined. No user input required before proceeding.

---

## Related

- [Granular Pipeline Checkpointing PRD](../granular-checkpointing/prd.md) — broader checkpointing work; this PRD covers the specific mid-loop resume gap for chunked outline and scene generation
- `prompts/agents/outline-planner.md` — Phase 3 (chunked outline loop)
- `prompts/agents/chapter-outline-expander.md` — Chapter expansion loop
- `prompts/agents/chapter-writer.md` — Scene generation loop
- `src/tools/outline_generator.py` — `cmd_expand_chapter`, `cmd_expand_to_scenes` (already idempotent)
- `src/tools/scene_writer.py` — `cmd_generate` (already idempotent)
