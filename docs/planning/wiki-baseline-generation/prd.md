# PRD: Wiki Baseline Generation — Pre-Story State

> Wiki initialization generates entity pages describing the world as it exists *before the story begins*, not as a summary of the full story arc.

**Date:** 2026-05-06
**Author:** Planner agent
**Status:** Draft

---

## Problem Statement

During the `wiki-generation` phase, `generate_character_pages()` and `generate_location_pages()` call `_build_outline_excerpt()` to construct the context passed to the LLM. This function assembles three sources: `story_elements`, `summary` (the full outline skeleton), and `chapter_outlines` (all chapter summaries as JSON). The LLM therefore sees the entire story arc — resolutions, deaths, relationship arcs, location changes — when generating the initial wiki page.

This produces incorrect baseline pages. `L3_current_state` ends up reflecting the end-of-story state; `L3_relationships` includes relationships formed during the story; `L3_growth_arc` describes the arc as if it has already happened. The wiki is supposed to be a *benchmark* — a clean pre-story snapshot that gets updated as chapters are written. Seeding it with full-arc knowledge defeats the purpose entirely.

The `story_elements` field was explicitly designed as a pre-story foundation. Its prompt (`prompts/multistep/outline/story_elements.md`) instructs the LLM to describe all characters at their **initial state at the story's beginning, before any story events occur**. This is the correct input for wiki baseline generation. The `summary` and `chapter_outlines` fields are plot-progression artefacts that belong to story execution, not baseline setup.

---

## Goals

1. Wiki character and location pages generated during `wiki-generation` describe entities as they exist at the start of the story, not across the full arc.
2. The `L3_current_state` and `L3_relationships` fields on character pages reflect opening condition, not post-story state.
3. Entity extraction (identifying *which* entities exist) retains access to the full outline so all named entities are discovered, even those introduced only late in the story.
4. The fix is backward-compatible — the `generate_character_pages` and `generate_location_pages` function signatures do not change; no pipeline-level changes are required.

---

## Non-Goals

- Changing how the wiki is *updated* during chapter writing (the update/snapshot/maintenance pipelines are out of scope).
- Changing the `wiki-bootstrap` phase or ChromaDB indexing.
- Retroactively fixing already-generated wikis for existing stories (no migration tooling).
- Adding new fields to `OutlineResult` or the pipeline state.

---

## User Stories

### Story Author

- As a story author, I want the wiki's initial character pages to describe who each character *is* at the start of the story, so that the wiki serves as an accurate baseline I can compare against as the story evolves.
- As a story author, I want location pages to describe places as they exist at the story's opening, so that environmental changes caused by plot events are visible when the wiki is later updated.

### Developer / Maintainer

- As a developer, I want the wiki page generation logic to clearly separate "entity discovery context" (full outline) from "page content context" (pre-story only), so the intent is self-documenting.

---

## Proposed Solution

### Summary

Separate the context used for **entity extraction** from the context used for **page content generation**. Entity extraction keeps the full outline so all named entities (even late-appearing ones) are discovered. Page generation receives only the pre-story foundation (`story_elements` + `base_context`), ensuring all field values describe the opening state.

The prompt templates are also updated to reinforce this framing — "current state" means "current state at story opening", "growth arc" means "potential arc trajectory inferred from initial conditions", etc.

### Backend (`src/tools/wiki_generation.py`)

Introduce a new helper `_build_pre_story_excerpt(outline_result, story_root)` that assembles only `story_elements` and `base_context` — omitting `summary` and `chapter_outlines`. This function is used for all `_generate_page()` calls.

`_build_outline_excerpt()` (used for `_extract_entities()`) is unchanged, preserving full-outline entity discovery.

The signatures of `generate_character_pages()` and `generate_location_pages()` are unchanged.

### Prompt Updates

`prompts/wiki/generate_character_page.md`:
- Rename the input variable from `outline_excerpt` to `pre_story_context` to signal intent.
- Reframe all field descriptions: `L3_current_state` → "character's condition at the *opening* of the story"; `L3_growth_arc` → "trajectory and potential arc *as inferred from initial conditions*, not events that will unfold"; `L3_relationships` → "relationships as they stand *at story start*".
- Add an explicit rule: "Describe the character only as they exist at the story's opening. Do not describe events that occur during the story."

`prompts/wiki/generate_location_page.md`:
- Same rename (`pre_story_context`) and explicit rule: "Describe the location only as it exists at the story's opening."
- `L3_current_state` → "condition of the location at the story's opening".

### Database / Storage

No schema changes. Wiki pages are stored identically; only their *content* is more accurate.

---

## Acceptance Criteria

- [ ] `_build_pre_story_excerpt()` exists in `wiki_generation.py` and returns only `story_elements` + `base_context`, never `summary` or `chapter_outlines`.
- [ ] `generate_character_pages()` passes `pre_story_excerpt` (not `outline_excerpt`) to all `_generate_page()` calls.
- [ ] `generate_location_pages()` does the same.
- [ ] `_extract_entities()` still receives the full `outline_excerpt` (entity discovery is unchanged).
- [ ] `generate_character_page.md` prompt explicitly instructs the LLM to describe the character at story opening only.
- [ ] `generate_location_page.md` prompt explicitly instructs the LLM to describe the location at story opening only.
- [ ] Unit tests verify `_build_pre_story_excerpt()` excludes `summary` and `chapter_outlines`.
- [ ] Existing unit tests for `generate_character_pages()` and `generate_location_pages()` continue to pass.

---

## Open Questions

- None. The approach is straightforward; no architectural decisions are deferred.

---

## Related

- ADR 014 (`docs/planning/adr/014-wiki-as-entity-source-of-truth.md`) — wiki as entity source of truth
- ADR 004 (`docs/planning/adr/004-progressive-wiki-memory-system.md`) — progressive wiki memory system
- `docs/planning/wiki-source-of-truth-consolidation/` — original wiki generation implementation planning
