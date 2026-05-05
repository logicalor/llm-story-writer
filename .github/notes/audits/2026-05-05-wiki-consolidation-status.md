# Audit — 2026-05-05 — Wiki Consolidation Status

**Audit Type:** Targeted code+data audit (no multi-model synthesis)
**Audit Scope:** Whether ADR 004 / PR #345 wiki-consolidation actually consolidated character sheets, setting sheets, and recaps into the wiki + ChromaDB
**Overall Health:** **At Risk** — consolidation is partial and one critical sync path is silently dead
**Repo:** datacrystals/AIStoryWriter, branch `development`

User question (verbatim):
1. whether character/setting sheets and recaps have ChromaDB embedding
2. why character/setting sheets and recaps still exist outside the wiki
3. where exactly wiki interrogation happens to supplement prompts

---

## Q1 — ChromaDB Embedding for Sheets and Recaps

**Verdict: Sheets are NOT embedded. Recaps are NOT embedded. Only wiki pages are embedded — and the wiki is not getting the recap or sheet content.**

### Evidence — collections actually present on disk

`chromadb.PersistentClient(path='.chromadb').list_collections()`:

| Collection | Count | Purpose |
| ---------- | ----- | ------- |
| `wiki-breaking-amy` | 29 | Wiki pages only |
| `wiki-the-silence-between-the-stars` | 9 | Wiki pages only |
| `wiki-the-silence-between-stars` | 2 | Wiki pages only |
| `wiki-test-story` | 22 | Wiki pages only |
| `audits`, `codebase`, `conventions`, `reflections`, `tests` | various | Repo memory, unrelated |

**No `stories-{name}` collection exists for any story.** The `stories-*` collection is the schema defined by [src/tools/rag_query.py](src/tools/rag_query.py#L32) for indexing `character`, `setting`, `recap`, `chapter`, `outline`, `wiki`, `raw-chapter` content. It is never populated by the active pipeline.

### Code paths that DO write to ChromaDB

1. **`wiki-{story}` collection** — written exclusively by `_upsert_to_chromadb()` in [src/tools/wiki_update.py](src/tools/wiki_update.py#L43). Called from `run_batch()` (lines 519, 601) and during create/update single-page handlers (lines 226, 324). This is invoked from:
   - [src/tools/_wiki_api.py](src/tools/_wiki_api.py#L440) `update_wiki_from_chapter()` → wired to `WikiMaintainerAgent.run()` ([src/presentation/agents/wiki_maintainer.py](src/presentation/agents/wiki_maintainer.py#L65))
   - [src/tools/wiki_extract.py](src/tools/wiki_extract.py#L640) `_bootstrap_single_wiki_entity()` → `run_batch()` (Phase wiki-bootstrap)
   - [src/presentation/orchestrator.py](src/presentation/orchestrator.py#L155) `_sync_recap_events_to_wiki()` → `run_batch()` (post-recap step)

2. **`stories-{story}` collection** — written only from:
   - [src/tools/rag_query.py](src/tools/rag_query.py) — CLI tool, never invoked from orchestrator
   - [src/presentation/cli/rag_cli.py](src/presentation/cli/rag_cli.py) — interactive helper, never invoked from orchestrator
   - [src/application/strategies/outline_chapter/character_manager.py](src/application/strategies/outline_chapter/character_manager.py#L619) `index_character()` and [setting_manager.py](src/application/strategies/outline_chapter/setting_manager.py#L610) `index_setting()` — **dead code path** (see Q2)

### Code paths that DO NOT write to ChromaDB

- `_generate_character_sheets()` in [orchestrator.py L639](src/presentation/orchestrator.py#L639) — writes JSON+md to `stories/<name>/characters/<slug>/`. No chroma upsert.
- `_generate_setting_sheets()` in [orchestrator.py L964](src/presentation/orchestrator.py#L964) — writes JSON+md to `stories/<name>/settings/<slug>/`. No chroma upsert.
- `RecapWriterAgent.run()` in [recap_writer.py](src/presentation/agents/recap_writer.py#L70) — returns `{events, compact, sanitised}` strings. Caller writes them to disk as markdown refs ([orchestrator.py L1923](src/presentation/orchestrator.py#L1923)). No chroma upsert for `compact` or `sanitised`. Only `events` are forwarded to `_sync_recap_events_to_wiki` — which is broken (see Q3 / [F-C-02]).

### Net effect

```
Source artefact           ChromaDB?           Indirect via wiki?
─────────────────────────────────────────────────────────────────
characters/*.json         No                  Partial (bootstrap-time only)
characters/**/*.md        No                  Partial (bootstrap-time only)
settings/*.json           No                  Partial (bootstrap-time only)
settings/**/*.md          No                  Partial (bootstrap-time only)
chapters/*_recap.json     No                  No (sync silently dead)
recap_events.md           No                  No (sync silently dead)
recap_compact.md          No                  No
recap_sanitised.md        No                  No
chapter_N.md (prose)      No                  No
wiki/**/*.md              Yes (`wiki-X`)     —
```

The compact/sanitised recap text and chapter prose are completely outside any vector index, despite being the highest-value content for similarity retrieval.

---

## Q2 — Why Sheets and Recaps Still Exist Outside the Wiki

**Verdict: ADR 004 / PR #345 implemented the read-side of consolidation (chapter writer reads wiki snapshot first) but kept all the upstream write paths and storage locations untouched. The sheets and recaps are still authoritative for everything except the chapter-writer prompt.**

### Sheets — current architecture

The active path is [src/presentation/orchestrator.py](src/presentation/orchestrator.py) (the strategy-pattern code under `src/application/strategies/outline_chapter/` is dead — `StrategyFactory` is referenced only in README and never instantiated). The orchestrator runs:

1. **Phase `characters`** → `_generate_character_sheets()` — name extraction → per-character chunked sheet generation → writes `characters/<slug>.json` + `characters/<slug>/{sheet,abridged,summary,chunks/*}.md`. **No wiki write. No chroma write.**
2. **Phase `settings`** → `_generate_setting_sheets()` — same pattern under `settings/`. **No wiki write. No chroma write.**
3. **Phase `wiki-bootstrap`** → `_list_wiki_entities()` ([wiki_extract.py L591](src/tools/wiki_extract.py#L591)) reads the sheet markdown files plus the outline text, runs entity extraction, and `_bootstrap_single_wiki_entity()` creates wiki pages for each. ChromaDB is populated as a side-effect of `run_batch()`.
4. **Per-chapter loop** → `WikiMaintainerAgent.run()` re-runs entity extraction on the new chapter prose and patches existing wiki pages.

After step 3, the sheet files become **stale derivatives**:
- They are not re-read after bootstrap to update the wiki.
- The wiki is not used to update them.
- No agent retires or deletes them.
- They remain on disk indefinitely.

### Sheets — why they still get consulted at all

Two surviving consumers of raw sheet content:

1. [src/presentation/agents/chapter_writer.py L181-197](src/presentation/agents/chapter_writer.py#L181-L197) — fallback path:
   ```python
   if wiki_snapshot:
       base_context = wiki_snapshot
       character_context = ""
       setting_context = ""
   else:
       (base_context, character_context, setting_context) = self._build_entity_context(story_name)
   ```
   `_build_entity_context()` ([L316-370](src/presentation/agents/chapter_writer.py#L316)) reads `<story>/characters/*.json` and `<story>/settings/*.json` directly. This fallback fires whenever `wiki/` does not exist OR `get_snapshot()` raises.
2. [src/tools/scene_writer.py L197-240](src/tools/scene_writer.py#L197) — accepts `character_sheets` / `setting_sheets` CLI flags. Standalone tool, not invoked by orchestrator's chapter loop, but exposed to users and any prompt that does multistep scene drafting via this CLI.

### Recaps — current architecture

Active path is [orchestrator.py L1862-1957](src/presentation/orchestrator.py#L1862):

1. `RecapWriterAgent.run()` produces `{events: str, compact: str, sanitised: str}`. Each is the raw LLM text — typically a fenced JSON block for `events` and free-form prose for `compact`/`sanitised`.
2. All three are written to `chapters/chapter_N/recap_{events,compact,sanitised}.md` and registered as `$ref` pointers in `state.recaps[str(chapter_number)]` and `chapter_N_recap.json`.
3. **Conditionally** ([L1941](src/presentation/orchestrator.py#L1941)): `if recap_result.get("events"): _sync_recap_events_to_wiki(...)` is called. This is intended to push events into wiki event pages.
4. `compact` and `sanitised` are **never** synced anywhere — they are read directly by the chapter writer for "previous chapter recap" context ([chapter_writer.py L201-211](src/presentation/agents/chapter_writer.py#L201)).

### Why consolidation didn't happen

ADR 004 ([docs/planning/adr/004-progressive-wiki-memory-system.md L58](docs/planning/adr/004-progressive-wiki-memory-system.md#L58)) explicitly stated:

> The wiki coexists with (and partially supersedes) the existing character sheets and setting sheets — these artifacts become the initial data source for wiki population but the wiki becomes the authoritative source after initialization.

The implementation honoured "wiki becomes authoritative for chapter-writer prompt" and stopped there. None of the following migration steps that were required to actually retire the parallel structures were performed:

- Sheet generation phases (`characters`, `settings`) were not removed.
- Sheet-evolver agents were retired (good — per [prior synthesis 2026-05-04](.github/notes/audits/2026-05-04-pr345-wiki-consolidation-synthesis.md)) but the **frozen sheets are still kept on disk** rather than deleted/migrated after wiki bootstrap.
- `chapter_writer._build_entity_context()` and the sheet-reading fallback were not removed.
- `scene_writer` CLI still requires sheet text input.
- Recap `compact`/`sanitised` outputs were never schema-mapped onto a wiki page type. There is no "chapter recap" wiki page, no "narrative summary" page type — only event pages, which carry only the per-event subset.
- No backfill: existing stories' sheets and recaps were not migrated into ChromaDB or wiki.

The audits from 2026-05-04 already identified this in [U-W-01] ("Three-way split confirmed antipattern — ADR 004 mandate not yet completed") — that issue remains open in practice even though ADR 004 was marked Accepted.

### Concrete on-disk evidence (story `breaking-amy`)

```
stories/breaking-amy/characters/  → 5 JSON sheets + 5 chunk dirs (amy, celeste, david, merv, sarah)
stories/breaking-amy/settings/    → 4 JSON sheets (mervs-apartment, communal-bathroom, drug-alcove, gray-park)
stories/breaking-amy/wiki/characters/  → 5 .md pages
stories/breaking-amy/wiki/locations/   → 3 .md pages   ← MISSING the-communal-bathroom
stories/breaking-amy/wiki/events/      → EMPTY        ← recap-event sync produced 0 pages
stories/breaking-amy/chapters/chapter_*_recap.json → 4 recaps with full events/compact/sanitised refs
```

Two-way divergence already happened: settings sheet count (4) ≠ wiki location count (3), and 4 chapter recaps produced 0 wiki event pages.

---

## Q3 — Where Wiki Interrogation Happens

**Verdict: Wiki is interrogated in exactly two narrow places, both inside the chapter writer. Outline, story-elements, character-sheet generation, setting-sheet generation, narrative-arc analysis, recap writer, consistency checker, story metadata, and final editor never touch the wiki.**

### Map of wiki-aware call sites in the active pipeline

| Caller | Location | What it queries | Fallback |
| ------ | -------- | --------------- | -------- |
| `ChapterWriterAgent.run()` | [chapter_writer.py L168-187](src/presentation/agents/chapter_writer.py#L168) | `get_snapshot(story, chapter, scene=0, outline=chapter_summary)` — full chapter-level snapshot | falls back to `_build_entity_context()` reading raw sheet JSONs |
| `ChapterWriterAgent._run_scene_pipeline()` | [chapter_writer.py L598-624](src/presentation/agents/chapter_writer.py#L598) | `get_snapshot(story, chapter, scene=N, outline=scene_desc, pov_character=…, characters=…, primary_location=…)` — scene-level snapshot | silently swallows exception, reuses chapter `base_context` |

That's it. Every other prompt assembled in the pipeline is wiki-blind:

- `OutlinePlannerAgent` — uses outline savepoint data, no wiki query
- `StoryPlannerAgent` (narrative-arc) — uses outline + story state, no wiki query
- `_generate_character_sheets` — uses `story_elements` + `base_context` (extracted from prompt), not wiki
- `_generate_setting_sheets` — same
- `ConsistencyCheckerAgent` — verify against outline / chapter, no wiki
- `RecapWriterAgent` — uses chapter content + previous recap, no wiki
- `WikiMaintainerAgent` — *writes* to wiki, doesn't *read* from it for context
- `StoryMetadataAgent` — uses outline + chapter 1 content
- `FinalEditorAgent` — uses chapter prose

### What `get_snapshot()` actually does

[src/tools/wiki_snapshot.py L1054](src/tools/wiki_snapshot.py#L1054) implements the ADR 005 three-stage hybrid retrieval pipeline:

1. **Stage 1 — multi-tier retrieval** (`_build_snapshot()`):
   - **T1 — entity match** ([L120](src/tools/wiki_snapshot.py#L120)): regex/alias match the outline text against `wiki/index.md` entries; force-include POV character + primary location.
   - **T2 — metadata query** ([L153](src/tools/wiki_snapshot.py#L153)): ChromaDB `collection.get(where={type=plot_thread, status=active})` and `where={type=world_rule}` from the `wiki-{story}` collection.
   - **T3 — semantic search** ([L210](src/tools/wiki_snapshot.py#L210)): ChromaDB `collection.query(query_texts=[outline], n_results=10)` against the same `wiki-{story}` collection.
   - **T4 — wikilink traversal** ([L255](src/tools/wiki_snapshot.py#L255)): one-hop follow of `[[slug]]` links found in already-retrieved page bodies.
   - Tier outputs are RRF-fused into a single ranked candidate set.
2. **Stage 2 — detail-level selection (L1/L2/L3)** with token budget enforcement (default 15000 tokens).
3. **Stage 3 — structured assembly** of a multi-section markdown document grouped by entity type.

`refresh_if_stale()` is called per-doc-id to lazy-update ChromaDB rows from source markdown when the file's mtime/sha256 has changed.

### Effective coverage of wiki interrogation

- Wiki snapshot is built from `wiki-{story}` ChromaDB only.
- That collection contains only wiki page bodies (created by bootstrap + per-chapter wiki maintainer).
- It contains no character-sheet chunks, no setting-sheet chunks, no recap text.
- Therefore semantic search in T3 cannot retrieve anything that lives only in sheets or recaps.
- T2 cannot retrieve `event` pages either, because zero event pages exist (recap-event sync is dead, see [F-C-02]).

The retrieval pipeline is well-engineered, but the corpus it queries is impoverished. The most narratively important content — character backstories at sheet-chunk granularity, per-chapter recaps, scene-level cause/effect — is invisible to it.

---

## Findings

### Critical

- **[F-C-01] Character sheets, setting sheets, and recaps are not embedded into ChromaDB.** Active orchestrator never calls `rag_query` index, never calls `_upsert_to_chromadb` for sheet/recap content. Wiki bootstrap only extracts a stub entity per sheet and writes a derivative wiki page; the sheet body itself is never indexed. Recaps are never indexed at all — neither raw events, compact, nor sanitised. Confirmed by listing `.chromadb/` collections — no `stories-*` collection exists. → ADR 004 mandate unfulfilled.

- **[F-C-02] Recap → wiki event sync is silently dead.** [orchestrator.py L1941](src/presentation/orchestrator.py#L1941) calls `_sync_recap_events_to_wiki(story, chapter, recap_result.get("events"))`. `recap_result["events"]` is the raw LLM string, typically wrapped in a `\`\`\`json … \`\`\`` fence (verified in `stories/breaking-amy/chapters/chapter_1/recap_events.md`). [orchestrator.py L70](src/presentation/orchestrator.py#L70) `_coerce_event_list` calls `json.loads(value)` on that fenced string, raises `JSONDecodeError`, returns `[]`, and `_sync_recap_events_to_wiki` returns `{created: 0, updated: 0}` without error. **All four chapters of `breaking-amy` produced zero wiki event pages.** Result: timeline page empty, no event pages searchable, T2 metadata query never retrieves events.

- **[F-C-03] Sheet/wiki divergence already manifesting.** `breaking-amy` has 4 setting sheets but only 3 wiki location pages (`the-communal-bathroom` exists as sheet, missing as wiki page). Bootstrap extraction is non-deterministic and lossy; without ChromaDB embedding of sheets, content is silently lost forever after bootstrap.

### Warning

- **[F-W-01] Recap compact/sanitised text never enters wiki or ChromaDB.** These are the prose summaries the chapter writer actually injects as `previous_chapter_recap`. They are read direct from disk via `read_markdown_ref` ([chapter_writer.py L201-211](src/presentation/agents/chapter_writer.py#L201)). Not searchable, not deduplicated, not retrievable from any other agent's prompt assembly.

- **[F-W-02] Wiki is queried only by the chapter writer.** Eight other agents (outline, story planner, character/setting generation, consistency checker, recap writer, wiki maintainer, story metadata, final editor) assemble prompts without consulting the wiki, so any wiki-corrected fact never propagates back into them. Consistency checker in particular is paradoxical — it validates against the outline but not against the wiki that ostensibly holds the latest verified entity state.

- **[F-W-03] Sheet read fallback in `chapter_writer._build_entity_context()` re-introduces stale data on any wiki failure.** Sheets are frozen after bootstrap, so on a wiki failure mid-story the chapter writer silently regresses to chapter-1-era entity descriptions. No warning emitted to user beyond the snapshot exception line.

- **[F-W-04] `outline_chapter/` strategy package is dead code with active ChromaDB integration.** [character_manager.py L314](src/application/strategies/outline_chapter/character_manager.py#L314) and [setting_manager.py L318](src/application/strategies/outline_chapter/setting_manager.py#L318) DO call `rag_integration.index_character/index_setting`. `StrategyFactory` is never instantiated outside docs. This means the integration that would partially address [F-C-01] exists in the codebase but is unreachable. Either revive the strategy-factory dispatch or delete the dead code.

- **[F-W-05] Two parallel ChromaDB schemas exist.** `wiki-{story}` (used) and `stories-{story}` (defined, never populated). [src/tools/rag_reconcile.py L190](src/tools/rag_reconcile.py#L190) reconciles the unused `stories-*` collection. Risk of future confusion / mis-routed queries.

### Info

- **[F-I-01] `WikiMaintainerAgent` reads chapter prose but not the wiki.** Its update logic re-extracts entities from chapter text, then asks the LLM to merge — without supplying the existing wiki page bodies (only `_read_compact_page` for slug-collision check). Drift opportunity.

- **[F-I-02] `recap_writer` returns LLM text wrapped in code fences without parsing.** `_run_stage` returns raw response text. The caller stores it as a markdown ref without unwrapping. This is the proximate cause of [F-C-02] and would also break any future "embed recap events into ChromaDB" path that naively `json.loads`-es the stored content.

- **[F-I-03] No backfill tool exists.** Stories generated before PR #345 (or with broken event sync) cannot have their sheets/recaps retroactively pushed into wiki/ChromaDB without manual re-running of bootstrap + per-chapter wiki maintainer. There is no `backfill_wiki_from_existing_story.py`.

---

## Recommended Actions (in priority order)

1. **Fix [F-C-02]**. In `_coerce_event_list`, strip `\`\`\`json` / `\`\`\`` fences before `json.loads`, and tolerate trailing prose. Add an integration test that runs the full recap → sync → wiki path with realistic LLM-style fenced output. Backfill `breaking-amy` events to validate.
2. **Fix [F-C-01]**. Decide one of:
   - **(A — preferred per ADR 004)** Push sheet chunk markdown and recap markdown directly into the `wiki-{story}` collection as `type: character_chunk | setting_chunk | recap_compact | recap_sanitised | recap_events` documents, so semantic search retrieves them. Drop the `stories-{story}` collection entirely. Update T2/T3 wiki snapshot logic to filter on wiki page types only.
   - **(B — minimum viable)** Wire the existing `outline_chapter/character_manager.index_character()` (or an equivalent thin helper) into `_generate_character_sheets`/`_generate_setting_sheets`/recap-write step, populating the `stories-{story}` collection. Then have `wiki_snapshot` query both `wiki-{story}` and `stories-{story}` (less clean — perpetuates the split).
3. **Fix [F-W-02]**. At minimum, have `ConsistencyCheckerAgent` and `RecapWriterAgent` request a wiki snapshot (cheap one — POV character + primary location only) before composing their prompts.
4. **Address [F-C-03]**. After wiki bootstrap, write a migration step that diffs sheet count against wiki page count per type, and fails the phase if any sheet was dropped. Or — if A above is adopted — bypass the lossy entity-extraction step entirely by upserting sheet chunks directly.
5. **Resolve [F-W-04]**. Either delete `src/application/strategies/outline_chapter/` (the dead strategy) or rewire the strategy factory.
6. **Backfill tool [F-I-03]**. Provide `python -m tools.backfill_wiki --story breaking-amy` that re-runs sheet→wiki extraction and recap→event sync for all existing chapters.

---

## Actions Taken

- Notes written: `.github/notes/audits/2026-05-05-wiki-consolidation-status.md`
- ChromaDB: findings ready for embed into `audits` collection (pending user approval)
- Issues created: **none** — pending user instruction on hand-off to Orchestrator
