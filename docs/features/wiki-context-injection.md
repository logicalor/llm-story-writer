# Wiki Snapshot Context Injection

> Issue #342 — `ChapterWriterAgent` now injects live wiki context into every chapter and scene generation call via the four-tier retrieval pipeline.

## Overview

Before issue #342, `ChapterWriterAgent` built its `base_context` entirely from the story-foundation fields extracted at pipeline startup (`outline_result.base_context`). After issue #342, the agent first attempts to assemble a fresh, token-budgeted wiki snapshot for the specific chapter and scene being written, and uses that snapshot as `base_context` when one is available.

Issue #344 tightens that contract: `_build_entity_context()` is now fallback-only. The chapter writer reads flat character and setting sheets from disk only when no wiki snapshot is available, making the live wiki the primary source of chapter-generation context.

The snapshot is produced by the four-tier retrieval pipeline already implemented in `src/tools/wiki_snapshot.py` ([ADR 005](../planning/adr/005-hybrid-wiki-context-retrieval-pipeline.md)). Calling `get_snapshot()` from inside the agent makes that pipeline an active participant in generation rather than a passive reference tool.

## Behaviour

### Chapter-level injection

In `ChapterWriterAgent.run()`, after building the initial entity context but before constructing the chapter prompt:

1. Checks whether `stories/<name>/wiki/` exists.
2. Calls `get_snapshot(story_name, chapter=N, scene=0, outline=chapter_summary)`.
3. If the call returns a non-`None` string, uses that snapshot as the chapter `base_context` and skips `_build_entity_context()` entirely.
4. Falls back silently to `_build_entity_context()` when:
   - The wiki directory is absent.
   - The ChromaDB collection for the story is empty or missing.
   - `get_snapshot()` returns `None` for any other reason (it never raises).

### Scene-level injection

In `ChapterWriterAgent._run_scene_pipeline()`, once per scene before drafting:

1. Calls `get_snapshot()` with the scene description as `outline`, plus `pov_character`, `characters`, `primary_location` (from the scene descriptor), and `scene_type`.
2. Assigns the result to `scene_base_context` when non-`None`.
3. Falls back silently to the chapter-level `base_context` when `None`.

## Python API — `get_snapshot()`

```python
from src.tools.wiki_snapshot import get_snapshot

snapshot: str | None = get_snapshot(
    story_name="my-story",
    chapter=3,
    scene=2,
    outline="Yuki confronts Commander Voss about the signal logs.",
    pov_character="yuki-tanaka-oduya",    # wiki slug (optional)
    characters=["commander-voss"],         # extra wiki slugs (optional)
    primary_location="control-room",       # wiki slug (optional)
    locations=None,
    scene_type="dialogue",                 # optional: "dialogue"|"action"|None
    budget=15000,                          # token budget (default: 15000)
)
```

**Return value:** A structured markdown string with sections for Characters, Location, Active Plot Threads, World Rules, and Recent Events — or `None` if the wiki is absent, empty, or retrieval fails.

**Guarantee:** The function never raises. All errors are caught internally and result in a `None` return, so callers can safely treat `None` as "use fallback context".

## Retrieval Pipeline (Four Tiers)

`get_snapshot()` delegates to `_build_snapshot()` which implements the ADR 005 three-stage pipeline:

| Tier | Type | What it finds |
|------|------|---------------|
| T1 | Entity match | Wiki pages whose names appear verbatim in the outline text, plus the forced POV character and primary location slugs |
| T2 | Metadata query | All active plot threads and world rules from ChromaDB, regardless of outline mention |
| T3 | Semantic search | Top-N pages by embedding similarity to the outline text |
| T4 | Wikilink traversal | Pages directly linked via `[[wikilinks]]` from T1–T3 results (2-hop max) |

Results are merged with Reciprocal Rank Fusion (RRF, k=60) and pages below `SCORE_THRESHOLD=0.15` are dropped. Detail levels (L1/L2/L3) are assigned by relevance percentile; POV character and primary location are always L3. Token budgeting demotes lowest-scoring pages until the assembled context fits within `budget` tokens.

## Bootstrap Coverage Limitation

The snapshot pipeline can only retrieve what the wiki bootstrap phase managed to seed into `stories/<name>/wiki/`.

Entities with dedicated sheet files in `stories/<name>/characters/*.json` and `stories/<name>/settings/*.json` are bootstrapped from those structured sheets plus outline data, so initial coverage is strongest for characters and settings.

Other entity types such as `faction`, `item`, `plot_thread`, `location_detail`, and story-specific custom types do not have dedicated sheet files. During bootstrap they are seeded from outline-text extraction only. Their initial wiki coverage therefore depends on mention frequency and extraction accuracy; entities mentioned rarely, indirectly, or ambiguously in the outline may be missed.

Consequence: wiki bootstrap is most reliable for characters and settings. Other entity types may begin with incomplete coverage until later chapter updates introduce or clarify them.

## Fallback Contract

The injection is always non-blocking:

```
wiki/            present and non-empty → use snapshot
wiki/            absent                → use flat-sheet base_context
ChromaDB         empty or missing     → use flat-sheet base_context
get_snapshot()   raises (any cause)   → use flat-sheet base_context
get_snapshot()   returns None         → use flat-sheet base_context
```

Stories without a wiki (e.g., stories skipped the wiki-bootstrap phase) continue to work exactly as before.

## Key Files

| File | Role |
|------|------|
| `src/tools/wiki_snapshot.py` | Four-tier retrieval pipeline; exposes `get_snapshot()` public API |
| `src/presentation/agents/chapter_writer.py` | Calls `get_snapshot()` at chapter and scene level; falls back silently |
| `docs/features/wiki-maintainer.md` | Describes the wiki bootstrap and post-chapter update processes that populate the wiki used here |
| `docs/planning/adr/005-hybrid-wiki-context-retrieval-pipeline.md` | ADR specifying the retrieval architecture |

## Related

- [Wiki Maintainer](wiki-maintainer.md) — populates the wiki that this feature reads from
- [ADR 004](../planning/adr/004-progressive-wiki-memory-system.md) — progressive wiki memory design
- [ADR 005](../planning/adr/005-hybrid-wiki-context-retrieval-pipeline.md) — hybrid retrieval pipeline design
- [Tools Reference](../tools.md) — `wiki_snapshot.py` CLI and Python API entry
