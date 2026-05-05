# ADR 014: Wiki as Entity Source of Truth + Independent Recap Index

**Date:** 2026-05-05
**Status:** Proposed

## Context

ADR 004 declared the wiki the authoritative source for entity state with sheets serving as a one-time bootstrap input. PR #345 implemented the read-side (wiki snapshot before sheet fallback) but left every other surface in the original split-source state. The 2026-05-05 audit confirmed:

- Character and setting sheets remain on disk indefinitely and are still authoritative for several agents.
- Recaps are not embedded in any vector index.
- Per-chapter wiki sync covers only a subset of page types, supplied with no prior page context, and the recap-event sync is silently dead due to fenced-JSON parsing.
- Eight of ten pipeline agents do not consult the wiki.

A decision is required on how to complete consolidation. The user has confirmed: sheet generation is retired entirely (no intermediate promote step), recap indexing is per-chapter aggregate only (no per-event documents), and no backfill tool is required because the change applies to fresh stories only.

## Decision

### 1. Direct wiki generation; sheet phases removed

The `characters` and `settings` orchestration phases — and the agents that drive them (`character_sheet_generator`, `setting_sheet_generator`) — are removed from the pipeline. They are replaced by a single `wiki-generation` phase that runs after `outline` (and any outline review).

For each character and location named in the outline, the new phase invokes a direct-to-wiki prompt that produces:

- Full YAML frontmatter (`type`, `slug`, `aliases`, `confidence: verified`, `detail_levels` with byte counts, source-pointer + fingerprint metadata stubs).
- L1 summary — one paragraph (≤ 300 chars).
- L2 abridged dossier — ~1500 chars covering background, motivations, current state.
- L3 full body — chunked sections under headers (`## Background`, `## Personality`, `## Motivations`, `## Relationships`, `## Skills`, `## Growth Arc`, `## Current State` for characters; equivalent for locations).

The prompt absorbs the substance of the prior chunked sheet prompts but emits structured output suitable for `wiki_update.run_batch` create payloads. This means no intermediate sheet markdown ever exists on disk; the wiki page is the first and only artefact.

Two new prompts:
- `prompts/wiki/generate_character_page.md`
- `prompts/wiki/generate_location_page.md`

Removed prompts (or their entry points):
- `prompts/characters/*` and `prompts/settings/*` callers — the prompt files may remain temporarily as reference but are no longer loaded by any agent.

After this phase completes, `wiki-bootstrap` continues to run for entities the outline mentions that are not characters or locations (factions, items, plot threads, world rules, themes).

The `chapter_writer._build_entity_context` fallback that previously read sheets is deleted. Wiki snapshot absence is escalated to `StoryGenerationError` rather than silently falling back. No agent reads `<story>/characters/` or `<story>/settings/`; those directories never exist.

### 2. Independent recap ChromaDB index — chapter-aggregate only

A new collection `recaps-{story_name}` is introduced, separate from `wiki-{story_name}`. Recaps remain on disk as markdown refs (no change to ADR 011); the index is built from the same source.

Schema:

| Document kind | id format | body | scalar metadata |
| ------------- | --------- | ---- | --------------- |
| Per-chapter aggregate | `aggregate/{chapter}` | `compact + sanitised` concatenated | `story`, `chapter`, `kind=chapter_aggregate`, `participants` (pipe-joined slugs), `locations` (pipe-joined slugs), plus source-pointer + fingerprint per ADR 012 |

Exactly one document per chapter. Per-event extraction continues to feed the wiki event-page sync (separate concern; lives in the wiki collection), but is not separately indexed in `recaps-`.

ChromaDB metadata cannot hold lists; participants and locations are joined with `|` and post-processed at query time. Filtering by character is performed by `where_document` `$contains` against the joined string. The slim metadata + single document per chapter keeps the collection small (one row per chapter, ≤ a few hundred documents per story even for very long works) and predictable.

A new module `src/tools/recap_index.py` exposes:

```python
def upsert_recap(story_name, chapter, recap_payload) -> None
def query_recap(story_name, *, character=None, location=None, query_text=None,
                chapter=None, chapter_range=None, n_results=10) -> list[dict]
```

The orchestrator's recap step calls `upsert_recap` after persisting markdown refs.

### 3. Robust per-chapter wiki sync

The single LLM call that previously did "extract everything from chapter" is replaced with a **per-type extraction sweep** orchestrated by `update_wiki_full_pass()`:

- For each `_TYPE_TO_DIR` page type (excluding `contradiction`), run a type-specific extraction prompt that already exists or is added.
- For each candidate page produced, **load the existing wiki page body** (if any) and pass it into a merge prompt. The merge prompt returns a structured patch describing frontmatter changes + L1/L2/L3 updates + body append/replace; free-form rewrites are forbidden.
- Per-type result is logged on the bus: `[Wiki] type=<X> created=A updated=B`.
- Failure surfacing: if a type-pass returns zero candidates AND the chapter prose contains alias matches against existing pages of that type, emit `[Wiki] WARNING type=<X> extraction returned 0 but aliases matched: …`.

The recap-event sync inside `_sync_recap_events_to_wiki` is repaired: `_coerce_event_list` strips ` ```json ` / ` ``` ` fences, tolerates leading/trailing prose, and on parse failure emits an explicit error rather than swallowing it.

### 4. Wiki/recap context for every consumer

A new helper `src/tools/context_assembly.py::assemble_context(...)` returns a `(wiki_snapshot, recap_snippets)` tuple. Consumers and the variables they receive are enumerated in `wiki-context-consumers.md` and `recap-context-consumers.md`. The helper composes:

- `wiki_snapshot`: existing `get_snapshot()` call with the consumer's focus (POV character, primary location, keywords).
- `recap_snippets`: `query_recap()` against the recap index with consumer-supplied filters; results are chapter-aggregate documents.

Each affected agent receives new template variables (`{wiki_context}`, `{recap_context}`) added to its existing prompts.

### 5. No backfill, no migration

Existing stories under `stories/` are out of scope. They will be regenerated under the new pipeline. No `backfill_wiki` CLI is shipped. The orchestrator does not attempt to detect or migrate legacy on-disk sheet artefacts; if they exist they are simply ignored. The existing-story directory `stories/breaking-amy/` will be discarded or regenerated by the operator.

## Consequences

### Positive

- One source of truth for entity state — eliminates the divergence already observed in `breaking-amy`.
- No intermediate sheet artefacts: smaller filesystem footprint, fewer code paths, no "sheet vs wiki page" reconciliation logic anywhere.
- Recaps become queryable by participant, location, semantic content, and chapter.
- Per-chapter wiki coverage extends to every supported page type; zero-result warnings catch silent regressions.
- The dead `stories-{story}` collection schema is removed; ChromaDB has exactly two per-story collections (`wiki-`, `recaps-`).
- One LLM call per character/location at story setup (vs. seven chunked calls per character previously); same or lower cost.

### Negative

- Direct wiki generation prompts must be tuned to produce all three detail levels reliably; there is no longer a chunked sheet to fall back on if the structured output is partial. Mitigation: schema validation at write time; failed pages re-prompted up to N retries.
- Wiki sync becomes ~N× slower per chapter (N = number of page types being swept). Mitigated by per-type extraction being shorter prompts than the current omnibus and by parallel `asyncio.gather`.
- Existing stories are not migrated; operators with in-flight stories must regenerate them.

### Neutral

- Sheet prompt files in `prompts/characters/` and `prompts/settings/` may remain in the repository as reference material; they are no longer loaded.
- `assemble_context` becomes a chokepoint that all wiki/recap-aware agents flow through; future changes to retrieval semantics happen there, not in each agent.

## Compliance with prior ADRs

- ADR 003 (ChromaDB): preserved; one new collection per story.
- ADR 004 (progressive wiki memory): completes the unfulfilled Phase 7d work.
- ADR 005 (hybrid retrieval pipeline): preserved; recap index is orthogonal to wiki retrieval.
- ADR 011 (markdown pointer persistence): preserved; recaps still live on disk as refs, only an index is added.
- ADR 012 (ChromaDB source sync): preserved; recap index uses the same source-pointer + fingerprint contract.
- ADR 013 (wiki context injection): preserved and extended to recap context.
