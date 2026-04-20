# Audit: Story Workflow Confusion

**Date:** 2026-04-20
**Scope:** Full codebase audit for issues causing muddled/confused story workflow
**Categories:**
1. Tools generating incorrectly formatted or confusing output
2. Agents getting confused about story status or next steps
3. Instances where agents/tools follow instructions incorrectly and go off on tangents

---

## Executive Summary

The story workflow gets "muddled and confused" due to **3 critical architectural gaps**, **6 high-severity issues**, and **5 medium-severity issues** across tools, agents, and prompts. The root causes cluster around: (1) savepoint format ambiguity causing type confusion, (2) mismatched savepoint names between agents, and (3) missing pipeline steps that no agent is responsible for.

---

## 🔴 CRITICAL Issues

### C1. Savepoint Repository Returns Unpredictable Types ✅ FIXED

**Files:** `src/infrastructure/storage/savepoint_repository.py`, all tools in `src/tools/`

`load_savepoint()` returned different types depending on how data was saved:
- String data → returned string
- Dict/list saved as YAML frontmatter → returned parsed dict/list
- JSON string saved as data → YAML parsed it back as dict, not string

**Fix applied** (`src/infrastructure/storage/savepoint_repository.py`):
- `save_savepoint`: dict/list is now serialized as **JSON in the markdown body** with `format: json` in frontmatter (not YAML in frontmatter). Scalar types (str, int, float, bool) are stored directly in body — unchanged.
- `load_savepoint`: reads `format` key from frontmatter — if `json`, parses body as JSON and returns the Python dict/list; otherwise falls back to legacy formats.

All 57 existing tests pass. Backward compatible with existing savepoint files via legacy fallback branches.

**Remaining cleanup** (non-blocking): Callers that do `if not isinstance(data, str)` → `json.dumps(data)` can now be simplified since `load_savepoint` always returns the same Python type that was originally saved.

---

### C2. Resume Decision Table Uses Savepoint Names That Don't Exist

**File:** `.opencode/agents/story-orchestrator.md`

**Status: ✅ FIXED (PR #71)**

The orchestrator's resume table references `outline_complete`, `characters_complete`, `settings_complete`, `wiki_populated`. But:
- The outline-planner creates `outline_consolidated` (not `outline_complete`)
- The orchestrator is supposed to create `outline_complete` after the subagent returns, but this is ambiguous
- No mapping exists between internal savepoint names and pipeline milestone names

**Impact:** On resume, the orchestrator can't determine pipeline state correctly. It may re-run Phase 2 (outline) even though the outline is already complete, or skip to Phase 5 when Phase 4 (wiki init) hasn't run.

**Fix applied:** Added an explicit **milestone savepoint owners table** and **internal subagent savepoint coexistence** table in the orchestrator. The table documents:
1. Every milestone savepoint is created **by the orchestrator** after the named phase completes, never by subagents
2. Subagents create their own internal savepoints (e.g. `outline_consolidated`) that may coexist with the milestone
3. A rule to always use `savepoint-mgr list` (names only) to discover what exists at resume time, and map internal names to milestone names using the table

The individual phase steps already had `savepoint-mgr save` calls for each milestone — the fix was documentation/disambiguation, not code change.

---

### C3. `chapter_{N}/content` Savepoint Never Created

**File:** `src/tools/recap_manager.py`, `.opencode/agents/story-orchestrator.md`

**Status: ✅ FIXED (PR #71)**

`recap_manager.py` loads chapter content from savepoint `chapter_{N}/content`. But no tool creates this savepoint. The scene-writer creates `chapter_{N}/assembled` and individual `chapter_{N}/scene_{M}` savepoints. The orchestrator receives the assembled chapter text from the chapter-writer subagent but never saves it as a `content` savepoint before calling recap-manager.

**Impact:** Recap generation **always fails** with "chapter content not found."

**Fix applied:** Added `#### 8b-1. Persist Chapter Content` step between 8b (scene generation) and 8c (post-chapter wiki update) in the orchestrator. This step:
1. Receives the assembled chapter text from the chapter-writer (8b step 2)
2. Saves it as `chapter_{N}/content` savepoint via `savepoint-mgr`
3. Writes it to story state field `chapters.<N>.content` via `story-state`

Recap generation (8d) now has the savepoint it needs. Wiki lint, quality eval, and chapter savepoint (8e–8g) all run after the content is persisted, so a crash in any of those steps can resume from the saved chapter.

---

## 🟡 HIGH Issues

### H1. Consolidate Dumps Entire Outline Into Agent Context

**File:** `src/tools/outline_generator.py`, `cmd_consolidate()`

**Status: ✅ FIXED (PR #71)**

First-run consolidation returns the full outline JSON (potentially 10K+ tokens) in stdout. The agent must then write this to `state.json`, but the instructions say to use `story-state write --value` which requires passing the entire JSON as a CLI argument. While `--value-file` exists, the consolidate tool doesn't write to a file — it only outputs to stdout.

**Impact:** Context window pollution, potential shell argument overflow, agent confusion about whether consolidation succeeded.

**Fix applied:** Two changes:
1. `cmd_consolidate`: Changed success output to set `"outline": None` instead of `"outline": <full JSON>`. The outline is already saved as `outline_consolidated` savepoint — no need to echo it into stdout.
2. Orchestrator Phase 2 step 4: Updated to load outline from `outline_consolidated` savepoint via `savepoint-mgr` instead of inlining JSON in `--value`. The message now instructs to load via `story-state read --name <name> --field outline`.

---

### H2. Recap Filters to "High" Importance Only — Loses Continuity

**File:** `src/tools/recap_manager.py`, `_should_keep_event()`

**Status: ✅ FIXED (PR #71)**

Keeps only `importance == "high"` events. Medium events (character development, relationship changes, plot thread progression) are all discarded. This defeats the purpose of recaps for continuity.

**Impact:** Chapter generation loses continuity context. Later chapters drift because recaps are too sparse.

**Fix applied:** `_should_keep_event` now returns `True` for both `high` and `medium` importance events. Only `low` importance events are discarded. The docstring was updated to match.

---

### H3. Wiki Maintainer References Non-Existent `refined_outline` Savepoint

**File:** `.opencode/agents/wiki-maintainer.md`, Mode 1 Step 1

**Status: ✅ FIXED (PR #71)**

Told to load `refined_outline` or `initial_outline`. But `cmd_refine` saves to `refined_outline` only when called — if critique is disabled (the default), this savepoint never exists. And for chunked generation, the outline lives in `outline_consolidated`, not `initial_outline`.

**Impact:** Wiki population may fail to load the outline, or load an outdated version.

**Fix applied:** Mode 1 Step 1 now tries savepoints in order: `outline_consolidated` → `refined_outline` → `initial_outline` → `story-state read --field outline`. The first existing savepoint is used, covering all generation modes (chunked, critique-enabled, monolithic).

---

### H4. Critique Parser: All 6 Critics Use Identical Criteria

**File:** `src/application/services/critique_parser.py`

**Status: ✅ FIXED (PR #71)**

All critic types had the same 7 criteria with identical max scores (15/15/15/10/10/20/15). Running 6 critics produced 6 near-identical evaluations.

**Fix applied:** Each critic type now has differentiated criteria and weightings reflecting its perspective:
- `audiobook-producer`: prioritises pacing (20) and flow (20); structure deprioritised (5)
- `book-club-moderator`: prioritises character arc/theme (25) and details (15)
- `commercial-fiction-editor`: prioritises pacing (20), genre (20), structure (20)
- `literary-fiction-reviewer`: prioritises details (20) and flow (20); pacing deprioritised (5)
- `publishing-acquisitions-editor`: balanced across all; genre and pacing weighted (15 each)
- `subject-expert`: only details (30) and consistency (30) scored; pacing/genre zeroed out

Total max score remains 85 for all types. Each critic now produces meaningfully distinct feedback.

---

### H5. `story-state write` Silently Stores Non-JSON as Strings

**File:** `src/tools/story_state.py`, `cmd_write()`

**Status: ✅ FIXED (PR #71)**

When `--value` isn't valid JSON, it's stored as a plain string with no warning. Writing `--field chapters.1 --value "some text"` stores a string where a dict was expected. Deep-merge then silently fails.

**Impact:** State.json can accumulate malformed data that breaks downstream readers.

**Fix applied:** `_set_nested` now emits a warning to stderr when overwriting a dict field with a non-dict value (string, number, bool). The warning includes the field path and the type being written, so the agent can see exactly what went wrong.

---

### H6. Orchestrator Doesn't Save Assembled Chapter Before Post-Processing

**File:** `.opencode/agents/story-orchestrator.md`, Phase 8

**Status: ✅ FIXED (PR #71) — resolved together with C3**

After the chapter-writer returns the assembled chapter, the orchestrator proceeds to wiki update, recap, lint, and quality eval — but never explicitly saves the chapter content to state.json or as a savepoint. The chapter-writer creates scene-level savepoints, but the orchestrator needs to persist the final assembled chapter. Without this, resume after a crash in Phase 8c-8g loses the entire chapter.

**Impact:** Loss of chapter content on crash; recap generation fails (see C3).

**Fix applied:** The C3 fix (`#### 8b-1. Persist Chapter Content`) directly addresses this: step 2 saves to `chapter_{N}/content` savepoint, step 3 writes to `chapters.<N>.content` in story state. Both persistence mechanisms are now in place before any post-processing runs.

---

## 🟠 MEDIUM Issues

### M1. `_extract_json_block` Can Return Truncated JSON

**File:** `src/tools/_llm.py`

**Status: ✅ FIXED (PR #71)**

Bracket-matching fails on nested JSON with escaped quotes. Fallback returns `text[start:]` which may be truncated. Callers then get `JSONDecodeError` and fall back to degraded modes.

**Impact:** Scene definition parsing failures, recap generation failures — both cause fallback to degraded modes.

**Fix applied:** Replaced bracket-matching as primary extractor with `json.JSONDecoder().raw_decode()` — the stdlib parser correctly handles all escape sequences and nested structures. Returns the exact JSON end position. Bracket matching is now the fallback, used only when `raw_decode` raises `JSONDecodeError`.

---

### M2. Scene Definition Parse Prompt Says "Don't Rewrite" But Asks for JSON Reformatting

**File:** `prompts/scenes/parse_definitions.md`

**Status: ✅ FIXED (PR #71)**

The prompt says "Don't rewrite the contents - just reformat them into JSON" but then asks for fields like `dialogue`, `literary_devices`, `ending` that require creative interpretation. The LLM must both "not rewrite" and "generate new content" — a contradiction that produces inconsistent scene definitions.

**Impact:** Inconsistent scene definitions; LLM may hallucinate dialogue/events not in the outline.

**Fix applied:** Replaced both instances of the ambiguous instruction with: "Extract information verbatim from the outline where it exists. Do not fabricate content not present in the outline — for fields like `dialogue`, `literary_devices`, and `ending`, use an empty string if the outline does not explicitly provide the information."

---

### M3. `wiki-snapshot` Has No Diagnostic Output

**File:** `src/tools/wiki_snapshot.py`

**Status: ✅ FIXED (PR #71)**

Returns a text blob with no metadata about which entities were included, what detail levels were selected, or how the token budget was allocated. When scene generation goes off-track, there's no way to diagnose whether the context was wrong.

**Impact:** Undiagnosable context quality issues; agents can't self-correct bad context assembly.

**Fix applied:** Added an `entities` list to the `stats` output in `cmd_snapshot`. Each entry includes: `slug`, `type`, `detail_level`, `token_count`, `tiers` (which retrieval tiers contributed), `entity_match_score`, and `semantic_similarity`. Sorted by token count descending so the heaviest entities are listed first. Also added `import sys` (already present).

---

### M4. Outline Chunk Prompt Has Duplicate "CONTINUITY REQUIREMENTS" Sections

**File:** `prompts/outline/create_chunk.md`

**Status: ✅ FIXED (PR #71)**

The prompt has two sections both titled "CONTINUITY REQUIREMENTS" with overlapping but different content. The LLM may follow one and ignore the other, producing inconsistent outlines.

**Impact:** Inconsistent outline continuity; LLM may follow conflicting instructions.

**Fix applied:** Removed the second (generic, lines 69-75) duplicate. The first section (lines 36-44) is the authoritative one — it includes the `CRITICAL` prefix and detailed sub-items (Escalation Order, Character Development, Plot Thread Continuity, Pacing Consistency, Thematic Development).

---

### M5. `continue` Command Tells Agent to "Ask the User" But Orchestrator Can't

**File:** `.opencode/commands/continue.md`

**Status: ✅ FIXED (PR #71)**

Says "ask the user which story from the list above they want to continue." But the orchestrator agent is explicitly told "CRITICAL: Never use the `question` tool or ask the user for input." This creates a contradiction when the continue command is used in batch mode.

**Impact:** Agent may deadlock or ignore the instruction, picking a random story.

**Fix applied:** Changed to "default to the most recent story (by savepoint timestamp) instead of asking the user." This resolves the conflict with the orchestrator's no-questions constraint while still making forward progress.

---

## Summary Table

| ID | Severity | Category | Issue |
|----|----------|----------|-------|
| C1 | 🔴 Critical | Tool output | Savepoint repo returns unpredictable types |
| C2 | ✅ Fixed | Agent confusion | Resume table uses non-existent savepoint names |
| C3 | ✅ Fixed | Agent confusion | `chapter_{N}/content` savepoint never created |
| H1 | ✅ Fixed | Tool output | Consolidate dumps full outline into context |
| H2 | ✅ Fixed | Tool output | Recap filters to high-importance only |
| H3 | ✅ Fixed | Agent confusion | Wiki maintainer references non-existent savepoint |
| H4 | ✅ Fixed | Tool output | All 6 critics use identical criteria |
| H5 | ✅ Fixed | Tool output | `story-state write` silently stores non-JSON |
| H6 | ✅ Fixed | Agent confusion | Orchestrator doesn't save assembled chapter |
| M1 | ✅ Fixed | Tool output | `_extract_json_block` can return truncated JSON |
| M2 | ✅ Fixed | Agent tangent | Scene parse prompt contradicts itself |
| M3 | ✅ Fixed | Tool output | Wiki snapshot has no diagnostic output |
| M4 | ✅ Fixed | Agent tangent | Outline chunk prompt has duplicate sections |
| M5 | ✅ Fixed | Agent confusion | Continue command contradicts orchestrator constraints |

---

## Recommended Fix Priority

The **top 3 fixes** that would most improve workflow reliability:

1. **Fix C3** — Save assembled chapter as `content` savepoint (unblocks recap generation)
2. **Fix C2** — Align savepoint names between orchestrator and subagents (unblocks resume)
3. **Fix C1** — Standardize savepoint data format (eliminates type confusion throughout)

These three address the most common failure modes: recaps always failing, resume always confused, and data type mismatches causing silent corruption.
