# Task Breakdown: Mid-Chunk Resume for Outline and Scene Generation

> Implements [PRD](./prd.md)

**Date:** 2026-05-10

---

## Tasks

### Task 1: outline-planner — chunked outline resume

**Type:** backend (agent prompt)
**Estimated scope:** small
**Dependencies:** none

**Description:**

Rewrite the Phase 3 chunked generation section of `prompts/agents/outline-planner.md` so the agent scans existing `outline_chunk_*` savepoints before entering the loop and skips complete chunks.

The new procedure at the start of Phase 3 (chunked path):

1. Call `savepoint-mgr list` for the story and collect all savepoint names.
2. Filter for names matching `outline_chunk_{start}_{end}`. Parse `start` and `end` from each name to determine which chunk ranges are complete.
3. Reconstruct the ordered list of chunk ranges that _would_ be generated for `wanted_chapters` / `outline_chunk_size` (same as the loop would produce: `[1..chunk_size]`, `[chunk_size+1..2*chunk_size]`, ...).
4. For each _complete_ chunk range (savepoint exists): load `outline_chunk_{start}_{end}` directly via `savepoint-mgr load` and append the data to the in-context `chunk_outlines` accumulator. Do not call `expand-chapter`.
5. Identify the last complete chunk range. Load its `continuity_{start}_{end}` savepoint via `savepoint-mgr load` and assign it as `continuitySummary` for the next call. If no complete chunks exist, `continuitySummary` starts empty.
6. Find the first _incomplete_ chunk range. This is where the `expand-chapter` loop begins. Continue the loop normally from that range to the end.

After the loop, build `merged_outline` by concatenating all `chunk_outlines` entries (both pre-loaded and newly generated) in chapter order. This is identical to the existing consolidation step — the change is only in how the accumulator is populated.

**Acceptance Criteria:**

- [ ] Phase 3 (chunked path) begins with an explicit pre-loop scan: "Call `savepoint-mgr list`. Collect all names matching `outline_chunk_{start}_{end}`. Build the full ordered list of chunk ranges for `wanted_chapters` / `outline_chunk_size`. For each range with an existing savepoint: load the chunk outline directly and append to the accumulator — do not call `expand-chapter`."
- [ ] The instructions explicitly state how to seed `continuitySummary` from the last complete `continuity_{start}_{end}` savepoint before the first `expand-chapter` call.
- [ ] The instructions explicitly identify when `expand-chapter` should first be called (first range without an existing savepoint).
- [ ] The consolidation step (`merged_outline` = concatenation of accumulator) is unchanged in structure.
- [ ] Unit test: with `outline_chunk_1_5` and `outline_chunk_6_10` savepoints pre-written for a 15-chapter, chunk_size-5 story, verify the agent instructions would cause `expand-chapter` to be called only for range 11–15, not 1–5 or 6–10.

**Key Files:**

- `prompts/agents/outline-planner.md` — Phase 3 chunked path rewrite
- `tests/unit/test_outline_planner_agent.py` — add resume scenario test (if test file exists; else create)

---

### Task 2: chapter-outline-expander — per-chapter expansion resume

**Type:** backend (agent prompt)
**Estimated scope:** small
**Dependencies:** none

**Description:**

Rewrite the Workflow section of `prompts/agents/chapter-outline-expander.md` (Step 4, the chapter loop) to scan for existing `expanded_chapter_{N}_{N}` savepoints before entering the loop.

The new procedure at the start of Step 4:

1. Call `savepoint-mgr list` for the story and collect all savepoint names.
2. Filter for names matching `expanded_chapter_{N}_{N}`. Build the set of chapter numbers N that are already expanded.
3. Find `first_incomplete_chapter` = the smallest N in [1..`wanted_chapters`] that is NOT in the set. If all are complete, proceed directly to Step 5 (return complete).
4. If `first_incomplete_chapter > 1`: there is no agent-side continuity to load — the tool auto-loads `expansion_continuity_{N-1}_{N-1}` internally when `phase="chapter"`. Simply note that chapters 1 through `first_incomplete_chapter - 1` are already done.
5. Begin the `expand-chapter` loop from `first_incomplete_chapter` (not from 1). For chapters `first_incomplete_chapter` through `wanted_chapters`, proceed exactly as the current loop.

The `expand-to-scenes` step (Step 4d) is also within the loop. Apply the same skip logic: if `chapter_{N}/scene_definitions` savepoint exists, do not call `expand-to-scenes` for chapter N.

**Acceptance Criteria:**

- [ ] Workflow Step 4 begins with an explicit pre-loop scan for `expanded_chapter_{N}_{N}` savepoints and identification of `first_incomplete_chapter`.
- [ ] The loop starts at `first_incomplete_chapter`, not at 1.
- [ ] The instructions note that continuity seeding is handled by the tool internally (no agent action needed).
- [ ] Step 4d (`expand-to-scenes`) includes the same skip: check if `chapter_{N}/scene_definitions` exists; if so, skip `expand-to-scenes` for that chapter.
- [ ] Unit test: with `expanded_chapter_1_1` through `expanded_chapter_5_5` savepoints pre-written for a 10-chapter story, verify the agent instructions would cause `expand-chapter` to be called only for chapters 6–10.

**Key Files:**

- `prompts/agents/chapter-outline-expander.md` — Workflow Step 4 rewrite
- `tests/unit/test_chapter_outline_expander_agent.py` — add resume scenario test (if exists; else create)

---

### Task 3: chapter-writer — scene generation resume

**Type:** backend (agent prompt)
**Estimated scope:** small
**Dependencies:** none

**Description:**

Rewrite the Scene Generation Loop section of `prompts/agents/chapter-writer.md` to scan for existing `chapter_{N}/scene_{M}` savepoints before entering the loop, and skip `wiki-snapshot` + `scene-writer generate` for already-complete scenes.

The new procedure at the start of the Scene Generation Loop:

1. Call `savepoint-mgr list` for the story and collect all savepoint names.
2. Filter for names matching `chapter_{N}/scene_{M}` (for the current chapter number N). Parse M values to determine which scenes are already complete.
3. Find `first_incomplete_scene` = the smallest M in [1..`scene_count`] without a savepoint. If all scenes are complete, skip to the assembly step.
4. For scenes 1 through `first_incomplete_scene - 1`: they are already persisted. Do not call `wiki-snapshot`. Do not call `scene-writer generate`. The `scene-writer generate` tool will auto-load the previous scene from its savepoint for continuity — no agent-side action needed.
5. Begin the `wiki-snapshot` + `scene-writer generate` loop from `first_incomplete_scene`. Continue normally to the end.

Remove or replace the vague existing "Resuming from a savepoint" note with the explicit procedure above.

Also update the Savepoint Strategy table to document the pre-loop scan as the resume mechanism.

**Acceptance Criteria:**

- [ ] The Scene Generation Loop section begins with an explicit pre-loop scan for `chapter_{N}/scene_{M}` savepoints, identification of `first_incomplete_scene`, and a clear rule: do not call `wiki-snapshot` or `scene-writer generate` for scenes 1 through `first_incomplete_scene - 1`.
- [ ] The existing vague "Resuming from a savepoint" note is replaced by a reference to this procedure.
- [ ] The instructions note that `previous_scene` for the first generated scene is auto-loaded by `scene-writer generate` from the prior scene's savepoint — no agent-side loading required.
- [ ] The Savepoint Strategy table is updated to describe the pre-loop scan as the resume mechanism.
- [ ] Unit test: with `chapter_3/scene_1` through `chapter_3/scene_4` savepoints pre-written for a chapter with 8 scenes, verify the agent instructions would cause `wiki-snapshot` and `scene-writer generate` to be called only for scenes 5–8.

**Key Files:**

- `prompts/agents/chapter-writer.md` — Scene Generation Loop section rewrite, Savepoint Strategy table update
- `tests/unit/test_chapter_writer_agent.py` — add resume scenario test (if exists; else create)

---

## Notes

- All three tasks are independent and can be dispatched in any order or in parallel.
- No Python tool files change. No new savepoint names introduced.
- The granular-checkpointing PRD covers a broader set of sub-step checkpoints across all phases. This plan addresses only the specific mid-loop resume gap for the three chunked loops identified by the user.
- Test files may need to be created from scratch if they don't exist. Check `tests/unit/` before creating; follow existing patterns from `test_outline_planner_agent.py` and `test_outline_chunked.py`.
