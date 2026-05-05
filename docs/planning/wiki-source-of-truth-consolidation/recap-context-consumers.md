# Report 6 — Recap Context Consumers

> Comprehensive map of every pipeline step that would benefit from temporal/recap context, with the recap-window strategy and metadata filters each should receive. Implements user requirement #6 of the consolidation request. Driver helper: `assemble_context(scope=…, recap_window=…)` introduced in [tasks.md Task 7](./tasks.md). Underlying index: `recap_index.query_recap` from [Task 1](./tasks.md).

**Date:** 2026-05-05

## Index granularity reminder

The recap index holds **exactly one document per chapter** (`kind=chapter_aggregate`, body = compact + sanitised concatenated). All recap retrieval below operates over chapter aggregates; per-event documents do not exist in this collection. When agents need event-grain detail they read the wiki event pages instead (the wiki collection's `event` page type).

## Why a recap index

The current pipeline only uses one recap (the previous chapter) as input to the next chapter. Every other agent runs blind to prior chapter events. Common failure modes:

- Recap writer for chapter N invents a beat already covered by chapter N-3 because it cannot see N-3.
- Final editor cannot detect cross-chapter continuity breaks.
- Consistency checker validates against outline only, not actual recapped events.
- Story metadata (title/blurb generation) sees only the outline, not what actually happened.
- Chapter writer for chapter 8 cannot recall how a relationship developed across chapters 2–6.

The recap index turns chapter aggregates into a queryable temporal store keyed by character, location, keyword (semantic), and chapter.

## Summary table

| # | Pipeline step | File | Currently uses recap? | Recommended `recap_window` | Filters | Priority |
|---|---|---|---|---|---|---|
| 1 | Outline planner — initial run | `src/presentation/agents/outline_planner.py` | No | None | — | n/a |
| 2 | Outline planner — continuation | `src/presentation/agents/outline_planner.py` | No | `("chapter", N)` where N = up to 10 most recent aggregates | — | High |
| 3 | Story planner | `prompts/multistep/*` | No | `("chapter", 5)` | — | Medium |
| 4 | Wiki generation phase | `src/tools/wiki_generation.py` | No | None at story setup (no prior chapters yet) | — | n/a |
| 5 | Chapter writer — chapter prompt | `src/presentation/agents/chapter_writer.py` | Reads ONLY immediately-prior recap (`previous_chapter_recap`) | Keep prior-chapter recap unchanged AS `{previous_chapter_recap}`. Add new `{recap_context}` = top 5 chapter aggregates involving any cast member, ranked semantically against chapter outline | `participants contains <any cast slug>`; semantic on `query_text=chapter_outline_summary` | **Critical** |
| 6 | Chapter writer — scene prompt | same | No | top 3 aggregates filtered by scene POV + location, semantic match to scene description | `participants contains <pov>`, `locations contains <location>`, semantic | High |
| 7 | Consistency checker | `src/presentation/agents/consistency_checker.py` | No | `("chapter", N)` aggregates for last 3 chapters PLUS top 5 by character relevance | last 3 by `chapter desc` + `participants contains <cast>` | **Critical** |
| 8 | Recap writer — extract events | `src/presentation/agents/recap_writer.py` | No | top 5 most-recent aggregates per detected cast member; deduplication signal | `participants contains <slug>`, `chapter < current` | High |
| 9 | Recap writer — sanitise | same | No | Last sanitised aggregate of last chapter | `chapter=N-1` | Medium |
| 10 | Wiki maintainer — event page extraction | `src/tools/_wiki_api.py` | No | top 3 prior aggregates tagged with same locations/participants as current chapter — supplies prior context | filter as Task 5 merge step needs | Medium |
| 11 | Story metadata | `src/presentation/agents/story_metadata.py` | No | All chapter aggregates concatenated (cap 20k tokens; truncate by chapter desc if oversize) | none (all chapters) | Medium |
| 12 | Final editor | `src/presentation/agents/final_editor.py` | No | Aggregate of chapter being edited + immediately prior 2 chapters | `chapter in {N-2..N}` | High |
| 13 | Prose scrubber | `src/presentation/agents/prose_scrubber.py` | No | None | — | n/a |
| 14 | Quality reviewer | `src/presentation/agents/quality_reviewer.py` | No | Same as consistency checker | same | Medium |
| 15 | Chapter outline expander | `src/presentation/agents/chapter_outline_expander.py` | No | `("character", 3)` for protagonist | `participants contains <protagonist>` | Medium |

## Recap-window strategy semantics

Implemented in `assemble_context.recap_window`:

| Strategy | `query_recap` translation |
|---|---|
| `("character", N)` | per character in `characters=` argument, retrieve top-N aggregates by recency where `participants` contains slug; merge, dedupe by id, sort by `chapter desc`, cap at N |
| `("chapter", N)` | last N chapter aggregates (sort `chapter desc`, limit N) |
| `("location", N)` | per location in `locations=` argument, top-N aggregates filtered by `locations contains` |
| `("semantic", N)` | semantic search by `query_text=focus`, optional metadata filter narrowing |
| `("none", 0)` | skip — return empty list |
| Combined: list of strategies merged with reciprocal-rank fusion | for consumers needing both temporal-aggregate AND character-filtered (e.g. consistency checker) |

## Filters supported by `query_recap`

| Filter | Backed by | Notes |
|---|---|---|
| `character` | `participants` metadata, pipe-encoded; resolved via `where_document $contains "<slug>"` or post-filter on metadata | Slug is the canonical wiki page slug |
| `location` | `locations` metadata, pipe-encoded | Same approach |
| `query_text` | semantic search on body | Falls back to substring match if embeddings unavailable |
| `chapter` | metadata `chapter` exact | |
| `chapter_range` | metadata `chapter` `$gte`/`$lte` | |

Date and timestamp filters from the prior draft are **not implemented** in this iteration because the index is per-chapter aggregate and timestamps would have to come from per-event documents (which we no longer index). If date queries are needed later, they will be added to the wiki event-page collection.

## Token budget

| scope | Recap budget |
|---|---|
| `outline` | 1500 tokens (sparse — outline planner only needs anchor points) |
| `chapter` | 3000 tokens (5 aggregates × ~600 tokens) |
| `scene` | 2000 tokens (3 aggregates × ~600 tokens) |
| `consistency` | 4000 tokens (3 aggregates by chapter + 5 by character, deduped) |
| `recap` | 2500 tokens (5 aggregates for dedup signal) |
| `metadata` | 6000 tokens (full aggregates concatenated, truncated if oversize) |
| `final_edit` | 4000 tokens (3 aggregates) |

## Failure modes to surface

- Empty result for a window strategy that should have matched (e.g. `("character", 5)` for a chapter-3 protagonist returns 0 aggregates) → bus warning `[Recap] index empty for <slug> — earlier chapter indexing may have failed`.
- Index unavailable (ChromaDB error) → degraded-mode warning, recap context substituted with empty string and explicit `[recap context unavailable]` marker so the LLM knows it is operating without temporal grounding.
- Slug resolution missing for a `participants` query argument (no matching wiki character page) → query returns empty; bus warning identifies the unresolved name.

## Rollout order

The chapter writer integration (#5) is highest leverage — it is the single largest LLM call in the pipeline and benefits most from broader temporal context. Consistency checker (#7) is the second priority because the audit identified it as the agent most damaged by missing wiki/recap state. Final editor and metadata (Task 10) ship last.

## Cross-reference

This report and [wiki-context-consumers.md](./wiki-context-consumers.md) are the authoritative source for the prompt-template variable additions referenced by [tasks.md](./tasks.md) Tasks 8, 9, and 10. The two reports together define every change to `prompts/**` mandated by this PRD beyond the new wiki-generation, extraction, and merge prompts.
