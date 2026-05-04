# PRD: Wiki Context Injection for Chapter Generation

> Replace the static flat-sheet entity context in `ChapterWriterAgent` with dynamic, relevance-ranked wiki snapshots assembled by the existing four-tier retrieval pipeline.

**Date:** 2026-05-04
**Author:** Planner agent
**Status:** Draft

---

## Problem Statement

The Python `ChapterWriterAgent` currently assembles context for chapter and scene generation by reading flat JSON character/setting sheets from disk (`stories/<name>/characters/*.json`, `settings/*.json`). It loads every entity, truncates to the `abridged` field (or first 300 chars of the sheet), and concatenates them into a single string. This has two structural weaknesses:

1. **All entities, always.** Every character and setting is injected regardless of relevance to the current chapter or scene. This wastes context window and dilutes the signal — a minor background character gets as much prominence as the POV character.

2. **No semantic depth.** The wiki contains structured, layered knowledge: plot threads, world rules, timeline events, wikilink-traversable relationships, and three detail levels (L1/L2/L3) calibrated to token cost vs. informativeness. None of this is used. The LLM is writing prose from the equivalent of a character bullet list instead of a living story knowledge base.

The result is that chapters lack the dynamic, inference-driven contextual grounding that makes prose feel internally consistent and narratively aware. The wiki system was built precisely to solve this — but it is currently written to but never read from during generation.

---

## Goals

1. Replace `_build_entity_context()` in `ChapterWriterAgent` with a call to the wiki snapshot pipeline for chapter-level context (direct path and revision path).
2. Inject per-scene wiki snapshots in `_run_scene_pipeline()` — each scene gets a relevance-ranked context assembled from its own outline text, POV character, and primary location.
3. Graceful fallback: if the wiki collection is absent or empty, fall back silently to the existing flat-sheet behaviour.
4. No change to the generation prompt templates — the snapshot output is a structured markdown string that maps directly to the existing `base_context` parameter slot.

---

## Non-Goals

- **Tool-calling / dynamic retrieval mid-generation.** This PRD covers pre-generation context injection only. Giving the LLM a live `wiki-search` tool it can call during inference (OpenAI function-calling style) is a separate, harder problem and deferred — see ADR 013.
- **Changing prompt templates.** The snapshot output slots into `{base_context}` without template changes.
- **Wiki update or maintenance.** The wiki is read here, not written. `WikiMaintainerAgent` handles writes.
- **Changing `ConsistencyCheckerAgent`.** Out of scope.

---

## User Stories

### Story author (pipeline operator)

- As a story author, I want chapters to reflect current plot thread states, character arcs, and world rules so that prose is consistent with the established story world without me manually curating context.
- As a story author, I want each scene to be contextually aware of the specific characters and locations involved rather than receiving every entity in a flat list.

### Developer

- As a developer, I want the wiki retrieval to be a pure Python call (no subprocess) so it is testable, debuggable, and type-safe.
- As a developer, I want graceful fallback so that stories without a bootstrapped wiki (or with a stale/missing ChromaDB collection) still generate chapters normally.

---

## Proposed Solution

### Background: What already exists

`src/tools/wiki_snapshot.py` already implements the complete four-tier hybrid retrieval pipeline (ADR 005):

| Tier | What | How |
|---|---|---|
| T1 | Entity matching | Deterministic name/alias matching against wiki index |
| T2 | Metadata query | ChromaDB `where` filter for active plot threads + world rules |
| T3 | Semantic search | ChromaDB vector query against scene outline text |
| T4 | Wikilink traversal | Follow `[[wikilinks]]` from T1–T3 pages (2-hop) |

After retrieval, `_merge_and_score()` RRF-ranks pages and `_assemble_context()` produces a structured markdown string with character sections (POV, scene, background), location, plot threads, world rules, and timeline events — at detail levels (L1/L2/L3) chosen by relevance score.

This is exactly what `ChapterWriterAgent` needs. The work is primarily wiring, not building.

### Part 1 — Python API wrapper in `wiki_snapshot.py`

Extract a public, importable function from the existing CLI command logic:

```python
def get_snapshot(
    story_name: str,
    chapter: int,
    scene: int,
    outline: str,
    pov_character: str | None = None,
    characters: list[str] | None = None,
    primary_location: str | None = None,
    locations: list[str] | None = None,
    scene_type: str | None = None,
    budget: int = 15000,
) -> str | None:
    """Run the four-tier retrieval pipeline and return a snapshot string.

    Returns None if the wiki collection is absent or empty (caller should
    fall back to flat-sheet context).
    """
```

This function is already ~95% implemented inside `cmd_snapshot` — the wrapper extracts the logic into a callable form without touching the CLI surface.

### Part 2 — Chapter-level snapshot for direct path

In `ChapterWriterAgent.run()`:

1. After `_build_entity_context()`, call `get_snapshot()` with the chapter outline text, chapter number, scene 0 (chapter-level).
2. If a snapshot is returned, use it as `base_context` instead of the flat-sheet result.
3. If `get_snapshot()` returns `None` (wiki not bootstrapped), use the flat-sheet result as before.

The snapshot replaces `base_context` — `character_context` and `setting_context` parameters to `_draft_direct` are left intact (they map to separate prompt slots).

### Part 3 — Per-scene snapshot in `_run_scene_pipeline()`

In the scene loop inside `_run_scene_pipeline()`:

1. Extract `pov_character`, `primary_location`, and key entity names from the `scene` dict returned by the decomposition step.
2. Call `get_snapshot()` with the scene's description/outline text and extracted slugs.
3. Pass the snapshot as `base_context` to the scene prompt template (replacing the chapter-level `base_context` for this scene).
4. Fallback to the chapter-level `base_context` if the snapshot returns `None`.

This gives each scene its own tailored context window — the POV character gets L3 detail, secondary characters get L2, background characters get L1 headlines.

### Fallback chain

```
wiki snapshot available?
  ├── yes → use snapshot as base_context
  └── no (collection absent / empty / exception) → use _build_entity_context() result (current behaviour)
```

All exceptions from `get_snapshot()` are caught and logged to the token bus; they never fail generation.

---

## Acceptance Criteria

- [ ] `wiki_snapshot.get_snapshot()` is importable and callable from Python (not subprocess).
- [ ] Calling `get_snapshot()` with a valid story that has an initialised wiki returns a non-empty string.
- [ ] Calling `get_snapshot()` for a story with no wiki collection returns `None` within 100ms.
- [ ] `ChapterWriterAgent` uses the snapshot as `base_context` when available.
- [ ] `_run_scene_pipeline()` calls `get_snapshot()` per scene, not once per chapter.
- [ ] When the wiki is absent, generation proceeds identically to current behaviour (flat-sheet fallback).
- [ ] `ruff`, `mypy`, and `pytest tests/unit/` all pass.
- [ ] A unit test confirms `get_snapshot()` returns `None` when no ChromaDB collection exists for the story.
- [ ] A unit test confirms `ChapterWriterAgent` falls back to flat-sheet context when `get_snapshot()` returns `None`.

---

## Open Questions

- Should the per-scene snapshot `budget` be configurable via `config.yml`? (Suggested default: 15000 tokens, same as OpenCode agent.) Recommended: yes, add `wiki_snapshot_budget` to `GenerationSettings` in a follow-up.
- Should `get_snapshot()` be a public export from `tools/wiki_snapshot.py` or wrapped in a thin `src/tools/_wiki_context.py` helper? The former is simpler; the latter separates concerns better if the snapshot pipeline grows. Recommended: keep in `wiki_snapshot.py` for now.

---

## Related

- [ADR 005: Hybrid Wiki Context Retrieval Pipeline](../adr/005-hybrid-wiki-context-retrieval-pipeline.md)
- [ADR 013: Wiki Context Injection vs. Tool-Calling](../adr/013-wiki-context-injection-vs-tool-calling.md)
- `src/tools/wiki_snapshot.py` — existing four-tier retrieval implementation
- `src/presentation/agents/chapter_writer.py` — target integration point
