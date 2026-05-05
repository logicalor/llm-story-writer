# PRD: Wiki Source-of-Truth Consolidation + Recap Indexing

> Replace character/setting sheets with direct wiki page generation; index chapter recaps in ChromaDB as per-chapter aggregates queryable by character, location, keyword and chapter; make per-chapter wiki sync robust across all entity categories; and supply wiki/recap context to every pipeline step that benefits from it.

**Date:** 2026-05-05
**Author:** Planner agent
**Status:** Draft
**Related audits:**
- [.github/notes/audits/2026-05-05-wiki-consolidation-status.md](../../../.github/notes/audits/2026-05-05-wiki-consolidation-status.md)
**Supersedes Phase 7d of:** [docs/planning/adr/004-progressive-wiki-memory-system.md](../adr/004-progressive-wiki-memory-system.md)

---

## Problem Statement

ADR 004 mandated that the wiki become the authoritative store for entity state, with character and setting sheets serving only as a one-time bootstrap source. PR #345 implemented the read-side of that mandate (the chapter writer prefers a wiki snapshot before falling back to raw sheets) but left every upstream and downstream concern in the original split state. The 2026-05-05 audit confirmed:

- Character sheets and setting sheets are still generated as the primary deliverable of dedicated phases and remain the canonical artefact on disk; they are never embedded into ChromaDB and never updated after wiki bootstrap.
- Recaps (compact and sanitised prose) are written only to the per-chapter file system and consulted only by the next chapter's writer; they are not embedded, not searchable, and not addressable by character/setting/keyword.
- The recap → wiki event sync is silently dead because `_coerce_event_list` cannot parse the LLM's fenced-JSON output, producing zero event pages for the test story `breaking-amy` despite four chapter recaps.
- Wiki interrogation is restricted to two call sites inside the chapter writer; eight other agents (outline planner, story planner, character/setting generators, consistency checker, recap writer, wiki maintainer, story metadata, final editor) compose prompts without consulting the wiki, so corrected facts never propagate.
- Per-chapter wiki maintenance re-extracts entities from chapter prose without supplying existing page bodies as context, encouraging drift, and only updates a subset of page types reliably.

This plan resets the architecture to a single-source-of-truth model: characters and settings are generated directly as wiki pages with no intermediate sheet artefacts; recaps are first-class indexed entries; all consumer agents receive wiki and recap context. The plan applies to fresh stories only — existing stories will be regenerated.

## Goals

1. The wiki is the only place character and setting state ever exists. The dedicated `characters` and `settings` sheet phases are removed; their replacements emit wiki pages directly.
2. Each chapter's recap (compact + sanitised concatenated) is indexed as a single chapter-aggregate document in a dedicated ChromaDB collection, queryable by character, location, keyword (semantic) and chapter number.
3. Per-chapter wiki sync covers every supported page type (character, location, event, faction, item, plot_thread, world_rule, theme, relationship, timeline_entry) with explicit failure surfaces (no silent zero-result merges) and supplies prior page content as merge context.
4. Every pipeline step whose output quality is degraded by missing entity or temporal context receives a wiki snapshot (entities) and/or recap query (temporal) before its prompt is composed.

## Non-Goals

- Backwards compatibility with existing stories. No backfill tool is shipped. Existing stories under `stories/` will be regenerated from scratch under the new pipeline.
- Replacing ChromaDB with another vector store (out of scope; ADR 003 stands).
- Retiring the markdown-pointer persistence convention (ADR 011 stands).
- Adding new page types beyond what `_TYPE_TO_DIR` already supports.
- Restoring the dead `src/application/strategies/outline_chapter/` package; the active orchestrator in `src/presentation/orchestrator.py` is the only execution path and the strategy package will be deleted in a follow-up cleanup task.
- Per-event or per-scene recap indexing. The recap collection holds one aggregate document per chapter only; per-event extraction continues to feed the wiki event-page sync but is not separately indexed.

## User Stories

### Story author / operator

- As an operator, when a chapter completes, I want every wiki page type that was mentioned in the chapter to have been considered for update, so a faction or world rule that drifted in the prose surfaces in the wiki.
- As an operator, I want chapter recaps to remain authored as prose (compact + sanitised) but also be searchable later, so I can answer "what chapters did Amy and Merv share scenes in?" without re-reading every chapter.
- As an operator, I want characters and settings generated directly as wiki pages so there is exactly one place to look for any entity fact.

### Pipeline (downstream agent)

- As the consistency checker, I want the verified entity state from the wiki, so I can flag drift instead of re-validating against a stale outline.
- As the outline planner (continuation runs), I want existing wiki entities as context, so I do not invent contradictions when extending an outline.
- As the recap writer, I want a snapshot of the last few related recaps for the same characters/locations, so I do not duplicate or contradict prior summaries.
- As the chapter writer, I want both wiki entity context and a temporal recap window (relevant prior recaps, not just the immediately preceding chapter) when drafting later chapters.

## Proposed Solution

### Architecture changes (high level)

1. **Direct wiki generation replaces sheet phases**:
   - The `characters` and `settings` orchestrator phases are removed entirely along with their generator agents (`character_sheet_generator`, `setting_sheet_generator`).
   - Replaced by a single `wiki-generation` phase running after `outline` (and any outline review). For each character and location named in the outline, this phase calls a direct-to-wiki prompt that produces the page's frontmatter + L1/L2/L3 detail levels + body in one structured call. Pages are written via the existing `wiki_update.run_batch` create path (so ChromaDB upsert and `index.md` update happen atomically).
   - Two new prompts: `prompts/wiki/generate_character_page.md` and `prompts/wiki/generate_location_page.md`. They incorporate the substance of the prior chunked sheet prompts (background, personality, motivations, relationships, skills, growth_arc, current_state for characters; equivalent sections for locations) but require structured wiki-page output rather than free-form sheet markdown. The L1 summary is a one-paragraph blurb; L2 is the abridged dossier; L3 is the full chunked content concatenated under section headers.
   - The on-disk locations `<story>/characters/` and `<story>/settings/` cease to exist. Sheet generators, sheet loaders, and the `chapter_writer._build_entity_context` fallback are deleted. Wiki absence is escalated as a `StoryGenerationError`.
   - `wiki-bootstrap` is preserved for entities mentioned in the outline that are NOT characters or locations — it captures factions, items, plot threads, world rules, themes that the outline references.

2. **Recap index** — one ChromaDB collection per story `recaps-{story_name}`:
   - Exactly one document per chapter: `id = aggregate/{chapter}`, body = compact + sanitised concatenated.
   - Metadata: `story`, `chapter`, `kind=chapter_aggregate`, `participants` (pipe-joined character slugs detected in the chapter), `locations` (pipe-joined location slugs), plus source-pointer + fingerprint metadata per ADR 012.
   - Embedding is over the body, so semantic search over chapter recaps becomes possible. Filter dimensions: chapter (exact / range), participant slug (substring on `participants`), location slug (substring on `locations`), keyword (semantic).
   - No per-event documents. Per-event extraction continues to drive the wiki event-page sync (the recap_writer's `events` JSON), but those events live in the wiki collection as event pages.

3. **Wiki sync robustness overhaul** (per-chapter):
   - The wiki maintainer is rewritten to run two passes per chapter:
     - **Pass A — extraction**: enumerate ALL `_TYPE_TO_DIR` page types via per-type LLM extraction prompts (existing prompts for character/location/event; new ones for faction, item, plot_thread, world_rule, theme, relationship, timeline_entry).
     - **Pass B — merge**: for each candidate update, the existing wiki page body is loaded and supplied to the merge prompt; the LLM produces a structured patch (frontmatter + L1/L2/L3 + body), not free-form replacement.
   - Failure mode: if a type-pass produces zero candidates AND the chapter prose contains tokens that match aliases of any existing page of that type, emit a warning bus event so silent regressions surface.
   - The recap → wiki event sync is fixed: `_coerce_event_list` strips fences, tolerates leading/trailing prose, and on parse failure emits an explicit error to the bus rather than returning `[]`.

4. **Wiki/recap context injection at every consumer**:
   - A new helper `assemble_context(story, *, scope, focus, chapter=None, scene=None, characters=(), locations=(), keywords=(), recap_window=("character", 3))` returns `{wiki_snapshot: str, recap_snippets: list[str]}` for any agent to call.
   - Each agent that benefits (consistency checker, outline planner continuation, recap writer, story metadata, final editor, etc.) is updated to call it and pipe results into existing `{base_context}` and new `{wiki_context}` / `{recap_context}` template variables in their prompts.

### Backend (Python orchestrator)

- New module `src/tools/recap_index.py` — ChromaDB collection helpers (`upsert_recap`, `query_recap`).
- New module `src/tools/wiki_generation.py` — direct character/location wiki page generation driver.
- Modified `src/tools/wiki_update.py` — add per-type extraction prompts dispatch + page-body-aware merge; expose new programmatic API `update_wiki_full_pass()`.
- Modified `src/tools/_wiki_api.py` `update_wiki_from_chapter()` — replace single-pass extraction with the full per-type sweep.
- Modified `src/presentation/orchestrator.py` — remove `characters` and `settings` phases entirely; insert `wiki-generation` phase; recap step writes to recap index after persisting markdown.
- Deleted: `src/presentation/agents/character_sheet_generator.py`, `src/presentation/agents/setting_sheet_generator.py`, sheet-related code paths in `chapter_writer.py`, sheet-loading helpers wherever they appear.
- Modified `src/presentation/agents/recap_writer.py` — unwrap fenced JSON in events output before returning.
- Modified `src/presentation/agents/wiki_maintainer.py` — invoke new full-pass API; surface per-type stats.
- Modified `src/presentation/agents/chapter_writer.py` — delete `_build_entity_context` fallback; require wiki snapshot; consume recap window from index.
- Modified `src/presentation/agents/consistency_checker.py`, `outline_planner.py`, `story_metadata.py`, `final_editor.py` — call `assemble_context` and use new template variables.
- New module `src/tools/context_assembly.py` — the `assemble_context` helper.

### Database / storage

- New ChromaDB collection schema: `recaps-{story_name}` with one document per chapter (`id = aggregate/{chapter}`).
- The `wiki-{story_name}` collection schema is unchanged but populated more completely (every page type, not just character/location/plot_thread/world_rule).
- The unused `stories-{story_name}` schema is decommissioned; `rag_query.py`, `rag_reconcile.py`, `rag_cli.py` are deleted (covered by the dead-strategy cleanup task).
- On disk: `<story>/characters/` and `<story>/settings/` no longer exist. Recaps remain at `<story>/chapters/chapter_<n>/recap_*.md`. Wiki pages remain at `<story>/wiki/<type>/<slug>.md`.

### Frontend

- TUI: a new event line `[Wiki] type=<X> updated N pages` per type during chapter completion, replacing the single aggregate line. New event line `[Recap] indexed chapter N aggregate (P participants, L locations)`.
- CLI: no new commands. The `characters` and `settings` resume points are removed from the resume-phase enum; CLI flags referencing them are removed.

## Acceptance Criteria

- [ ] Running the full pipeline on a fresh story never creates `<story>/characters/` or `<story>/settings/` directories.
- [ ] Every entity in the outline that is a character or location has a wiki page of the corresponding type after the `wiki-generation` phase, with all three detail levels populated and `confidence: verified`.
- [ ] After each chapter completes, `recaps-{story}` collection grows by exactly one document with `kind=chapter_aggregate`.
- [ ] `query_recap(story, character="amy")` returns chapter aggregates whose `participants` metadata contains `amy`; `query_recap(story, query_text="confrontation")` returns by semantic search; `query_recap(story, chapter=3)` returns the chapter-3 aggregate.
- [ ] After a chapter completes, the wiki sync stats show non-zero per-type counts for at least the page types whose entities are mentioned in the chapter; zero-count + alias-match emits a warning bus event.
- [ ] Consistency checker, outline planner (continuation), recap writer, story metadata, and final editor receive wiki snapshots and recap snippets as documented in the consumer reports.
- [ ] The chapter writer no longer references sheet files; the `_build_entity_context` method is deleted; sheet generator agents are removed from the codebase; `grep -r "characters/" src/` returns no on-disk character-sheet path references.
- [ ] `_coerce_event_list` handles fenced JSON; an integration test runs the full recap → sync path with realistic LLM-style fenced output and produces wiki event pages.
- [ ] Documentation: ADR 004 status remains Accepted but body has a "Phase 7e (this PRD)" pointer; new ADR documents the direct-wiki-generation pattern + recap index design.

## Open Questions

None outstanding. The three deferred questions from the prior draft were resolved by the user:

- Sheet generation is **retired entirely** (no promotion intermediate). Direct-to-wiki prompts replace it.
- Recap index is **per-chapter aggregate only**. Per-event documents deferred indefinitely.
- **No backfill** ships. The plan applies to fresh stories; existing stories will be regenerated.

## Related

- ADR 004 (Progressive wiki memory system)
- ADR 005 (Hybrid wiki context retrieval pipeline)
- ADR 011 (Markdown pointer persistence)
- ADR 012 (ChromaDB source sync)
- This PRD will be supported by:
  - `docs/planning/adr/014-wiki-as-entity-source-of-truth.md` (new)
  - `docs/planning/wiki-source-of-truth-consolidation/wiki-context-consumers.md` (Report 5)
  - `docs/planning/wiki-source-of-truth-consolidation/recap-context-consumers.md` (Report 6)
