# Report 5 — Wiki Context Consumers

> Comprehensive map of every pipeline step (and notable subroutines) that would benefit from wiki context, with the variables and retrieval scope each should receive. Implements user requirement #5 of the consolidation request. Driver helper: `assemble_context(scope=…, …)` introduced in [tasks.md Task 7](./tasks.md).

**Date:** 2026-05-05

## Summary table

| # | Pipeline step | File | Currently uses wiki? | Recommended scope | New template variables | Priority |
|---|----|----|----|----|----|----|
| 1 | Outline planner — initial run | `src/presentation/agents/outline_planner.py` | No | Skip (no entities yet) | — | n/a |
| 2 | Outline planner — continuation/regeneration | `src/presentation/agents/outline_planner.py` | No | `scope="outline"`, focus=existing-outline + user prompt, characters=top-N from wiki, locations=top-N from wiki | `{wiki_context}` | High |
| 3 | Story planner (multistep) | `prompts/multistep/*` | No | `scope="outline"`, focus=outline | `{wiki_context}` | Medium |
| 4 | Wiki generation phase — character page | `src/tools/wiki_generation.py` (Task 3) | New phase | `scope="outline"`, focus=full outline; characters=other characters already generated (so cross-references stay coherent) | `{related_characters_context}` | High (within Task 3) |
| 5 | Wiki generation phase — location page | `src/tools/wiki_generation.py` | New phase | Same shape, `locations=` already-generated locations | `{related_locations_context}` | High (within Task 3) |
| 6 | Wiki bootstrap — outline-only entity extraction | `src/tools/wiki_extract.py` | Reads sheets historically; under Task 3 reads only the outline | After Task 3, takes already-generated character/location pages as exclude-set so the same entity is not double-bootstrapped | (no prompt change) | Low |
| 7 | Chapter writer — chapter prompt | `src/presentation/agents/chapter_writer.py` | Yes (post-#345) | `scope="chapter"`, pov_character, primary_location, characters=cast, keywords=chapter goals | `{wiki_context}` (already present); deepen with explicit `{character_context}`, `{location_context}` blocks composed from snapshot | Already done; tighten in Task 9 |
| 8 | Chapter writer — scene prompt | `src/presentation/agents/chapter_writer.py` | Yes (post-#345) | `scope="scene"`, pov_character=scene POV, primary_location=scene location, characters=scene cast | `{wiki_context}` (already present) | Already done |
| 9 | Consistency checker | `src/presentation/agents/consistency_checker.py` | No | `scope="consistency"`, focus=chapter draft summary, characters=cast extracted from draft, locations=settings extracted from draft. Wiki snapshot is the AUTHORITATIVE expected state to validate against | `{wiki_context}` (verified entity facts), `{wiki_relationships}` (sub-block of relationship pages) | **Critical** |
| 10 | Recap writer — extract events | `src/presentation/agents/recap_writer.py` | No | `scope="recap"`, focus=chapter draft, characters=detected cast. Wiki context here helps event extraction tag participants with stable slugs | `{wiki_context}` (alias→slug map for participants) | High |
| 11 | Recap writer — sanitise prose | same | No | Same scope as #10 but light — only canonical names | `{wiki_context}` (slim) | Medium |
| 12 | Wiki maintainer — per-type extraction (Task 5) | `src/tools/_wiki_api.py` | Reads existing pages | Each type-pass receives `{existing_pages_index}` (alias list) so the LLM can mark candidates as updates vs creates | `{existing_pages_index}` per type | **Critical** |
| 13 | Wiki maintainer — page-body merge (Task 5) | `src/tools/_wiki_api.py` | New | Each merge receives full prior page body and new candidate; LLM emits structured patch | `{existing_page_body}`, `{new_candidate}` | **Critical** |
| 14 | Story metadata (title/tags/blurb) | `src/presentation/agents/story_metadata.py` | No | `scope="metadata"`, focus=outline + first/last chapter compact, characters=top-N from wiki, keywords=themes from wiki | `{wiki_context}` | Medium |
| 15 | Final editor | `src/presentation/agents/final_editor.py` | No | `scope="final_edit"`, chapter-scoped — pov_character + primary_location + cast for the chapter being edited | `{wiki_context}`, `{recap_context}` (Report 6) | High |
| 16 | Prose scrubber | `src/presentation/agents/prose_scrubber.py` (or equivalent) | No | Optional — wiki is mostly irrelevant to prose-level cleanup; supply only `{character_aliases}` for canonical name correction | `{character_aliases}` | Low |
| 17 | Quality reviewer | `src/presentation/agents/quality_reviewer.py` | No | `scope="consistency"` (same retrieval as #9) | `{wiki_context}` | Medium |
| 18 | Chapter outline expander | `src/presentation/agents/chapter_outline_expander.py` (if active) | No | `scope="outline"`, focus=chapter outline | `{wiki_context}` | Medium |

## Retrieval shape per scope

`assemble_context(scope=...)` invokes `wiki_snapshot.get_snapshot(...)` with these shape parameters:

| scope | Detail level cap | Page-type filter | Token budget |
|---|---|---|---|
| `outline` | L2 | character, location, plot_thread, theme | 6000 |
| `chapter` | L3 (cast + primary location); L1 for everyone else | all | 12000 |
| `scene` | L3 (POV + present cast + scene location); L1 elsewhere | all | 8000 |
| `consistency` | L3 (cast); L2 (relationships, plot threads) | character, location, relationship, plot_thread, world_rule, event | 10000 |
| `recap` | L1 (cast canonical names + slugs only) | character, location | 2000 |
| `metadata` | L1 (top-N characters); L2 themes | character, theme | 4000 |
| `final_edit` | L3 (cast + location); L2 plot threads | character, location, plot_thread | 10000 |

## Prompt-template change inventory

Files that need new variables (`{wiki_context}` and friends) added to their templates:

- `prompts/outline/*` — continuation prompts only (initial outline excluded)
- `prompts/consistency_check/*`
- `prompts/recap/extract_events.md`, `prompts/recap/sanitize.md`
- `prompts/wiki/generate_character_page.md`, `prompts/wiki/generate_location_page.md` (Task 3) — receive `{related_characters_context}` / `{related_locations_context}`
- `prompts/wiki/extract_*` and `prompts/wiki/merge_page.md` — Task 4 + 5 already include these
- `prompts/story_state/*` — metadata prompts
- `prompts/final_edit/*`
- `prompts/chapter_review/*`
- `prompts/multistep/*` — story planner if it remains active

## Failure modes to surface

For every consumer that takes wiki context, the following must be observable:

- Empty wiki snapshot for a scope that should have produced one (e.g. `consistency` after chapter 2 returns empty) → bus warning; NOT silent empty-string substitution.
- Snapshot exceeded token budget and was truncated → bus info event with byte-count.
- Snapshot retrieval error (ChromaDB unavailable) → escalation to `StoryGenerationError` for chapter writer / consistency checker; degraded-mode warning for recap writer / metadata.

## Rollout order

The PR-345 audit's recommendation to feed verified wiki state to the consistency checker is the highest-leverage win and ships in Task 8 alongside outline-continuation context. Recap writer integration (#10, #11) ships in Task 9 with chapter writer hardening. Metadata + final editor (Task 10) ships last because they only run once at story-end.
