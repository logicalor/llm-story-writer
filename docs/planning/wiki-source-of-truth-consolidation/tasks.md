# Task Breakdown: Wiki Source-of-Truth Consolidation + Recap Indexing

> Implements [PRD](./prd.md). Architectural decisions in [ADR 014](../adr/014-wiki-as-entity-source-of-truth.md). Consumer mappings in [wiki-context-consumers.md](./wiki-context-consumers.md) and [recap-context-consumers.md](./recap-context-consumers.md).

**Date:** 2026-05-05

Tasks are ordered so each can be merged independently. Task 0 ships first as a hotfix because it is causing live data loss on every chapter. Tasks 1–3 establish the recap index and direct wiki generation. Tasks 4–6 deliver the wiki sync overhaul. Tasks 7–10 wire wiki/recap context into every consumer. Tasks 11–12 are cleanup and docs.

---

## Task 0: Fix recap-event JSON parsing (hotfix)

**Type:** backend
**Estimated scope:** small
**Dependencies:** none

**Description:**

`_coerce_event_list` in [src/presentation/orchestrator.py](../../../src/presentation/orchestrator.py#L68) calls `json.loads()` directly on the recap_writer's `events` output, which is consistently a fenced ` ```json … ``` ` block. The exception is caught, returns `[]`, and `_sync_recap_events_to_wiki` exits 0/0 without emitting any error. Fix the parser to strip leading/trailing fences and surrounding prose, and on genuine parse failure emit a bus error so silent regressions cannot recur.

**Acceptance Criteria:**

- [ ] `_coerce_event_list` accepts strings with optional ` ```json ` / ` ``` ` fences and surrounding prose; returns the inner array.
- [ ] On unparseable input the function raises `ValueError`; the orchestrator catches it and emits `[Recap] event parse failed: …` to the bus (no silent zero return).
- [ ] Unit test covers: bare JSON, fenced JSON, fenced JSON with leading prose, fenced JSON with trailing prose, malformed input.
- [ ] Integration test runs `_sync_recap_events_to_wiki` with realistic LLM-style fenced output and asserts at least one event page is created.

**Key Files:**

- `src/presentation/orchestrator.py` — fix `_coerce_event_list`, surface parse errors
- `tests/unit/test_orchestrator_recap_parse.py` — new
- `tests/integration/test_recap_event_sync.py` — new

---

## Task 1: Recap ChromaDB index module

**Type:** backend
**Estimated scope:** medium
**Dependencies:** Task 0

**Description:**

Create `src/tools/recap_index.py` providing the new per-story `recaps-{story_name}` collection. Implement `upsert_recap` and `query_recap` per ADR 014. Use `_chroma_sync.upsert_from_source` for fingerprint metadata. Pipe-encode list-valued metadata (`participants`, `locations`) for ChromaDB scalar compatibility; provide a `_split_pipe(s)` helper for query-time decoding.

The collection holds **exactly one document per chapter** (`id = aggregate/{chapter}`, `kind=chapter_aggregate`). No per-event documents. Body is `compact + sanitised` concatenated.

**Acceptance Criteria:**

- [ ] `upsert_recap(story_name, chapter, payload)` creates one aggregate document and only one (idempotent on rerun).
- [ ] Aggregate metadata includes `chapter`, `kind=chapter_aggregate`, `participants`, `locations`, plus source-pointer + fingerprint.
- [ ] `query_recap(story, character="amy")` returns aggregates whose `participants` metadata contains the slug `amy`.
- [ ] `query_recap(story, location="the-bathroom")` returns aggregates whose `locations` metadata contains the slug.
- [ ] `query_recap(story, chapter=3)` returns the chapter-3 aggregate; `query_recap(story, chapter_range=(2,4))` returns chapters 2,3,4.
- [ ] `query_recap(story, query_text="confrontation", n_results=5)` performs semantic search on bodies.
- [ ] Multiple filters compose with AND semantics.
- [ ] Unit tests cover all query dimensions against an in-memory ChromaDB collection populated with two synthetic chapters.

**Key Files:**

- `src/tools/recap_index.py` — new
- `tests/unit/test_recap_index.py` — new

---

## Task 2: Wire recap index into the orchestrator's recap step

**Type:** backend
**Estimated scope:** small
**Dependencies:** Task 1

**Description:**

After the orchestrator persists recap markdown refs ([orchestrator.py L1923](../../../src/presentation/orchestrator.py#L1923)), call `recap_index.upsert_recap(story_name, chapter, recap_result)`. Move this OUT of the `if recap_result.get("events"):` guard so chapters without enumerated events still index the compact + sanitised aggregate. Wire a TUI/bus event `[Recap] indexed chapter N aggregate (P participants, L locations)`.

Slug resolution for `participants` and `locations` metadata: use a simple alias lookup against the existing wiki `index.md` for character and location pages. Unknown names are dropped (not stored as raw strings) — they would not match any wiki page anyway.

**Acceptance Criteria:**

- [ ] On chapter completion, `recaps-{story}` collection grows by exactly one document.
- [ ] Eventless chapters still produce an aggregate document.
- [ ] Resume after partial failure does not duplicate documents (upsert idempotency verified).
- [ ] Bus emits indexed event with participant/location counts.

**Key Files:**

- `src/presentation/orchestrator.py` — recap step block

---

## Task 3: Direct wiki generation phase + sheet phase removal

**Type:** backend
**Estimated scope:** large
**Dependencies:** none (parallelisable with Task 1)

**Description:**

Remove the `characters` and `settings` orchestrator phases entirely. Delete the agents `src/presentation/agents/character_sheet_generator.py` and `src/presentation/agents/setting_sheet_generator.py`, their tests, and any sheet-loading helpers consumed by other agents.

Add new module `src/tools/wiki_generation.py`:

- `generate_character_pages(story_name, outline) -> {generated: int, skipped: int}` — iterates outline characters, runs the new prompt to produce a structured wiki page, writes via `wiki_update.run_batch` create payload.
- `generate_location_pages(story_name, outline) -> {...}` — symmetric for locations.

Add new orchestrator phase `wiki-generation` between outline (and outline review) and `wiki-bootstrap`. The phase calls both functions sequentially.

Add prompts:
- `prompts/wiki/generate_character_page.md` — takes outline excerpt + character name; emits frontmatter + L1 (≤300 chars) + L2 (~1500 chars) + L3 (chunked sections under headers). Output schema validated by the writer; failed pages retry once.
- `prompts/wiki/generate_location_page.md` — symmetric.

Update orchestrator phase enum + resume logic to drop `characters` and `settings`. Delete CLI flags referencing them.

Delete `chapter_writer._build_entity_context` and the sheet-fallback branch. Wiki snapshot absence becomes `StoryGenerationError`.

**Acceptance Criteria:**

- [ ] Pipeline run on a fresh story never creates `<story>/characters/` or `<story>/settings/`.
- [ ] Every outline character has a `wiki/characters/<slug>.md` with all three detail levels populated and `confidence: verified`.
- [ ] Every outline location has a `wiki/locations/<slug>.md` similarly populated.
- [ ] Resume after partial `wiki-generation` does not regenerate already-written pages.
- [ ] `grep -r "character_sheet_generator\|setting_sheet_generator" src/` returns no matches after this task.
- [ ] Unit tests for `generate_character_pages` happy path + retry-on-bad-schema.

**Key Files:**

- `src/tools/wiki_generation.py` — new
- `prompts/wiki/generate_character_page.md`, `prompts/wiki/generate_location_page.md` — new
- `src/presentation/orchestrator.py` — phase removal + new phase
- `src/presentation/agents/character_sheet_generator.py`, `setting_sheet_generator.py` — delete
- `src/presentation/agents/chapter_writer.py` — delete `_build_entity_context`
- `tests/unit/test_wiki_generation.py` — new
- delete obsolete tests for sheet generators

---

## Task 4: Per-type wiki extraction prompts

**Type:** prompts
**Estimated scope:** medium
**Dependencies:** none

**Description:**

The current `_wiki_api._prepare_chapter_update` runs one omnibus extraction. Replace with per-type prompts. For types that already have prompts (`character`, `location`, `event`), keep them; add new ones for the remaining `_TYPE_TO_DIR` types. Each prompt asks the model to extract entities of ONE type from chapter prose, with strict JSON-array output.

Add prompts:
- `prompts/wiki/extract_factions_from_chapter.md`
- `prompts/wiki/extract_items_from_chapter.md`
- `prompts/wiki/extract_plot_threads_from_chapter.md`
- `prompts/wiki/extract_world_rules_from_chapter.md`
- `prompts/wiki/extract_themes_from_chapter.md`
- `prompts/wiki/extract_relationships_from_chapter.md`
- `prompts/wiki/extract_timeline_from_chapter.md`

**Acceptance Criteria:**

- [ ] Each new prompt loads via `PromptLoader` without template errors.
- [ ] Manual smoke test: each prompt run on chapter 1 of a fresh-pipeline story returns valid JSON parseable by the existing `_parse_json_response`.

**Key Files:**

- `prompts/wiki/*.md` — seven new files

---

## Task 5: Page-body-aware merge prompt + full-pass driver

**Type:** backend
**Estimated scope:** large
**Dependencies:** Task 4

**Description:**

Replace the single-shot extract+merge in `_prepare_chapter_update` with two passes:

1. **Per-type extraction sweep** — `asyncio.gather` of one extraction call per page type, using prompts from Task 4.
2. **Page-body-aware merge** — for each candidate, load the existing wiki page body via `_read_compact_page` (or full body when no compact L1 exists), feed both old body and new candidate to a new `prompts/wiki/merge_page.md` prompt that emits a structured patch.

Add new public function `update_wiki_full_pass(story_name, chapter, chapter_text, *, model=None, base_url=None)` that drives both passes and returns `{per_type: {character: {created, updated}, …}, total_created, total_updated}`.

Add zero-result + alias-match warning: after each type pass, run `match_entities_in_text(chapter_prose, index_entries[type])`; if extraction returned 0 but matches > 0, emit `[Wiki] WARNING type=<X> 0 candidates but aliases matched: …`.

**Acceptance Criteria:**

- [ ] `update_wiki_full_pass` runs all per-type extractions in parallel and returns per-type stats.
- [ ] Merge prompt receives existing page body when an update is intended; new pages skip merge and use the creation flow.
- [ ] Zero-result + alias-match path emits the documented warning bus event.
- [ ] Integration test: run on a synthetic chapter mentioning entities of every type; asserts each type produced ≥ 1 candidate.

**Key Files:**

- `src/tools/_wiki_api.py` — `_prepare_chapter_update` rewrite, add `update_wiki_full_pass`
- `prompts/wiki/merge_page.md` — new
- `tests/integration/test_wiki_full_pass.py` — new

---

## Task 6: Switch wiki maintainer agent to full-pass API

**Type:** backend
**Estimated scope:** small
**Dependencies:** Task 5

**Description:**

`WikiMaintainerAgent.run()` currently calls `update_wiki_from_chapter`. Switch to `update_wiki_full_pass` and surface per-type stats on `wiki_bus` (one `WikiContextEvent` per non-zero type) and `bus` (one summary line: `[Wiki] chapter N — character: +A/~B; location: +C/~D; …`).

**Acceptance Criteria:**

- [ ] After a chapter, the bus shows per-type stats.
- [ ] Existing tests still pass (the old `update_wiki_from_chapter` may be deleted or re-implemented as a thin shim that calls the full-pass).

**Key Files:**

- `src/presentation/agents/wiki_maintainer.py`

---

## Task 7: Context assembly helper

**Type:** backend
**Estimated scope:** medium
**Dependencies:** Tasks 1, 2

**Description:**

New module `src/tools/context_assembly.py` exposing:

```python
def assemble_context(
    story_name,
    *,
    scope: Literal["outline", "chapter", "scene", "consistency", "recap", "metadata", "final_edit"],
    focus: str,                         # outline summary or scene description
    chapter: int | None = None,
    scene: int | None = None,
    pov_character: str | None = None,
    primary_location: str | None = None,
    characters: tuple[str, ...] = (),
    locations: tuple[str, ...] = (),
    keywords: tuple[str, ...] = (),
    recap_window: tuple[str, int] = ("character", 3),
    token_budget: int = 15000,
) -> {"wiki_snapshot": str, "recap_snippets": list[str]}
```

Internally calls `wiki_snapshot.get_snapshot` and `recap_index.query_recap` per the consumer mapping in [wiki-context-consumers.md](./wiki-context-consumers.md) and [recap-context-consumers.md](./recap-context-consumers.md).

`recap_window` strategies: `("character", N)` = N most recent chapter aggregates whose `participants` contain any of `characters`; `("chapter", N)` = N most recent chapter aggregates by chapter number; `("location", N)` = N most recent aggregates filtered by location; `("semantic", N)` = top-N semantic by `query_text=focus`; `("none", 0)` = skip recap.

**Acceptance Criteria:**

- [ ] Returns deterministic output for given inputs.
- [ ] Token budget split honoured: wiki_snapshot ≤ `token_budget * 0.7`, recap_snippets ≤ `token_budget * 0.3`.
- [ ] Unit tests for each scope variant.

**Key Files:**

- `src/tools/context_assembly.py` — new
- `tests/unit/test_context_assembly.py` — new

---

## Task 8: Consistency checker + outline planner integration

**Type:** backend
**Estimated scope:** medium
**Dependencies:** Task 7

**Description:**

Per [wiki-context-consumers.md](./wiki-context-consumers.md), add wiki and recap context to:

- `ConsistencyCheckerAgent.run()` — calls `assemble_context(scope="consistency", focus=chapter_summary, characters=outline_pov, …)`. Adds new `{wiki_context}` and `{recap_context}` template variables to consistency prompts.
- `OutlinePlannerAgent` continuation/regeneration paths — calls `assemble_context(scope="outline", …)` when the run is a continuation (story state already has approved chapters). Initial outline run skips wiki (no entities exist yet).

**Acceptance Criteria:**

- [ ] Consistency checker prompts receive populated `{wiki_context}` and `{recap_context}` blocks during chapter 2+ runs.
- [ ] Outline planner regeneration receives wiki snapshot when prior chapters exist.
- [ ] Existing prompts updated to render the new variables.

**Key Files:**

- `src/presentation/agents/consistency_checker.py`
- `src/presentation/agents/outline_planner.py`
- `prompts/consistency_check/*.md` — variable additions
- `prompts/outline/*.md` — variable additions on continuation prompts

---

## Task 9: Recap writer + chapter writer integration

**Type:** backend
**Estimated scope:** medium
**Dependencies:** Tasks 3, 7

**Description:**

- `RecapWriterAgent.run()` — call `assemble_context(scope="recap", chapter=N, characters=...)` to retrieve the last 3–5 recent chapter aggregates per character involved (extracted from chapter prose via simple alias match) and pass them as `{related_recap_history}` to `recap/extract_events.md` and `recap/sanitize.md`. Goal: prevent duplication / contradiction across chapters.
- `ChapterWriterAgent.run()` — replace direct recap-from-state lookup with `assemble_context(scope="chapter", chapter=N, pov_character=..., primary_location=...)`. The result's `recap_snippets` becomes the new `{recap_context}` template variable; the existing `{previous_chapter_recap}` is preserved (it remains a tightly-scoped just-prior-chapter signal, while `recap_context` is broader).

Note: chapter_writer's `_build_entity_context` deletion is owned by Task 3; this task only adds the recap context wiring.

**Acceptance Criteria:**

- [ ] Recap writer prompt receives `{related_recap_history}`.
- [ ] Chapter writer prompts receive `{recap_context}` in addition to existing `{previous_chapter_recap}`.
- [ ] Wiki snapshot failure still raises `StoryGenerationError` (regression guard from Task 3).

**Key Files:**

- `src/presentation/agents/recap_writer.py`
- `src/presentation/agents/chapter_writer.py`
- `prompts/recap/extract_events.md`, `prompts/recap/sanitize.md` — variable additions
- `prompts/chapters/*.md` — variable additions where chapter writer prompts are loaded

---

## Task 10: Story metadata + final editor integration

**Type:** backend
**Estimated scope:** small
**Dependencies:** Task 7

**Description:**

- `StoryMetadataAgent` — receive a wiki snapshot scoped to top entities and a chapter-aggregate recap window across all chapters when generating tags/title.
- `FinalEditorAgent` — receive a wiki snapshot keyed by per-chapter primary entities and a recap window covering the chapter being edited and the immediately prior 2 chapters.

**Acceptance Criteria:**

- [ ] Metadata prompt receives `{wiki_context}` listing top characters and themes.
- [ ] Final editor prompt receives chapter-scoped wiki + recap context.

**Key Files:**

- `src/presentation/agents/story_metadata.py`
- `src/presentation/agents/final_editor.py`
- `prompts/story_state/*.md`, `prompts/final_edit/*.md` — variable additions

---

## Task 11: Decommission `stories-{story}` collection + dead strategy package

**Type:** cleanup
**Estimated scope:** small
**Dependencies:** Tasks 1–10 merged

**Description:**

- Delete `src/application/strategies/outline_chapter/` (dead code per [audit 2026-05-05](../../../.github/notes/audits/2026-05-05-wiki-consolidation-status.md)).
- Delete `src/tools/rag_query.py`, `src/tools/rag_reconcile.py`, `src/presentation/cli/rag_cli.py`.
- Delete tests / docs referencing the strategy package or the unused RAG CLI.

No production code currently writes to `stories-{story}`, so no live ChromaDB cleanup is required.

**Acceptance Criteria:**

- [ ] `grep -r "stories-" src/` returns no matches.
- [ ] `grep -r "OutlineChapterStrategy\|StrategyFactory" src/` returns no matches.
- [ ] `mypy src/` and `pytest` clean.

**Key Files:**

- multiple deletions

---

## Task 12: Documentation refresh

**Type:** docs
**Estimated scope:** small
**Dependencies:** Tasks 1–11 merged

**Description:**

- Update [docs/planning/adr/004](../adr/004-progressive-wiki-memory-system.md) to add a "Phase 7e completed via PRD wiki-source-of-truth-consolidation" pointer.
- Mark ADR 014 status `Accepted`.
- Update `.github/copilot-instructions.md` if any conventions changed.
- Update `docs/manual.md` and `docs/tools.md`: remove references to character/setting sheets; add the new `wiki-generation` phase; document the recap index.
- Replace the audit recommendations section in `.github/notes/audits/2026-05-05-wiki-consolidation-status.md` with a "resolved" footer.

**Acceptance Criteria:**

- [ ] All referenced docs updated.
- [ ] ADR 014 status flipped to Accepted.

**Key Files:**

- `docs/planning/adr/004-progressive-wiki-memory-system.md`
- `docs/planning/adr/014-wiki-as-entity-source-of-truth.md`
- `docs/manual.md`, `docs/tools.md`
- `.github/notes/audits/2026-05-05-wiki-consolidation-status.md`
