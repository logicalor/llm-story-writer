# Task Breakdown: Wiki Context Injection

> Implements [PRD](./prd.md)

**Date:** 2026-05-04

---

## Tasks

### Task 1: Extract `get_snapshot()` Python API from `wiki_snapshot.py`

**Type:** backend
**Estimated scope:** small
**Dependencies:** none

**Description:**
`src/tools/wiki_snapshot.py` already contains all four retrieval tiers and the context assembly logic inside `cmd_snapshot()`. This task extracts that logic into a public, importable Python function `get_snapshot()` at module level.

The function signature:

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
```

Returns the assembled snapshot string, or `None` if the wiki collection is absent or empty (ChromaDB `NotFoundError`, collection count == 0, or any import/runtime error from chromadb).

`cmd_snapshot()` should be refactored to delegate to `get_snapshot()` so no logic is duplicated.

**Acceptance Criteria:**

- [ ] `from tools.wiki_snapshot import get_snapshot` works without error.
- [ ] `get_snapshot(story_name="nonexistent", chapter=1, scene=1, outline="test")` returns `None` within 200ms.
- [ ] `cmd_snapshot()` delegates to `get_snapshot()` (no duplicated pipeline logic).
- [ ] `mypy src/tools/wiki_snapshot.py` clean.
- [ ] Unit test: `test_get_snapshot_returns_none_when_no_collection` — patches `_get_collection` to return `None`, asserts return is `None`.
- [ ] Unit test: `test_get_snapshot_returns_string_when_collection_populated` — uses existing wiki fixture or mocked collection.

**Key Files:**

- `src/tools/wiki_snapshot.py` — extract `get_snapshot()`, refactor `cmd_snapshot()` to delegate
- `tests/unit/test_wiki_snapshot.py` — add two new tests (create file if absent)

---

### Task 2: Chapter-level snapshot injection (direct path)

**Type:** backend
**Estimated scope:** small
**Dependencies:** Task 1

**Description:**
In `ChapterWriterAgent.run()`, after `_build_entity_context()` is called, attempt to get a wiki snapshot for the chapter. If successful, replace `base_context` with the snapshot before passing it to `_draft_direct()` and `_run_scene_pipeline()`.

The chapter-level snapshot is assembled with `scene=0` (sentinel for "whole chapter") and the chapter's outline text as `outline`. Character slugs can be left empty at this level — the entity matching tier will find them from the outline text.

The fallback path (`_build_entity_context()` result) is used unchanged when `get_snapshot()` returns `None` or raises.

```python
# After _build_entity_context():
wiki_snapshot = None
try:
    wiki_snapshot = get_snapshot(
        story_name=story_name,
        chapter=chapter_number,
        scene=0,
        outline=chapter_summary,
    )
except Exception as exc:
    await self.bus.emit(f"\n[Wiki] snapshot failed ({type(exc).__name__}: {exc})\n")

if wiki_snapshot:
    base_context = wiki_snapshot
    await self.wiki_bus.emit(WikiContextEvent(
        phase="chapter",
        event_type="semantic_search",
        content=f"Wiki snapshot assembled for chapter {chapter_number}",
    ))
```

**Acceptance Criteria:**

- [ ] When wiki collection exists and is populated, `base_context` in generation prompts is the snapshot string, not the flat-sheet string.
- [ ] When wiki collection is absent, behaviour is identical to current (flat-sheet context).
- [ ] Exception in `get_snapshot()` is caught; generation proceeds with flat-sheet fallback.
- [ ] `WikiContextEvent` is emitted with `event_type="semantic_search"` when snapshot is used.
- [ ] Unit test: `test_chapter_writer_uses_wiki_snapshot_when_available` — mocks `get_snapshot` to return a string; asserts the mock return value appears in the prompt passed to `provider.generate_text`.
- [ ] Unit test: `test_chapter_writer_falls_back_when_wiki_unavailable` — mocks `get_snapshot` to return `None`; asserts `_build_entity_context` result is used instead.

**Key Files:**

- `src/presentation/agents/chapter_writer.py` — add wiki snapshot call in `run()`
- `tests/unit/test_chapter_writer_agent.py` — add two new tests

---

### Task 3: Per-scene snapshot injection in `_run_scene_pipeline()`

**Type:** backend
**Estimated scope:** medium
**Dependencies:** Task 1, Task 2

**Description:**
In `_run_scene_pipeline()`, replace the shared chapter-level `base_context` with a per-scene snapshot for each scene's prompt. Before generating each scene's prose, call `get_snapshot()` with:

- `outline`: the scene's `description` field from the scene definition dict
- `pov_character`: the first entry in `scene.get("characters", [])` (treated as POV by convention; can be refined later)
- `characters`: remaining entries in `scene.get("characters", [])`
- `primary_location`: `scene.get("setting", None)`
- `scene=index` (scene number within chapter)

If the per-scene snapshot is `None`, fall back to the chapter-level `base_context` already computed for this chapter.

Replace the `base_context` variable in the scene prompt template call with the scene-specific snapshot. The `previous_scene_tail` and `scenes_completed_summary` variables are unaffected.

**Acceptance Criteria:**

- [ ] Each scene receives a distinct snapshot call with its own `outline`, `pov_character`, and `primary_location`.
- [ ] Scenes for which `get_snapshot()` returns `None` use the chapter-level `base_context`.
- [ ] A snapshot failure for scene N does not affect scenes N+1 onward (each call is independent).
- [ ] Unit test: `test_scene_pipeline_calls_get_snapshot_per_scene` — mocks `get_snapshot` with a side_effect list; confirms it is called once per scene with different `outline` values.
- [ ] Unit test: `test_scene_pipeline_falls_back_per_scene_when_wiki_unavailable` — `get_snapshot` returns `None`; asserts chapter-level `base_context` is used for each scene.

**Key Files:**

- `src/presentation/agents/chapter_writer.py` — inject per-scene snapshot in `_run_scene_pipeline()`
- `tests/unit/test_chapter_writer_scene_pipeline.py` — add two new tests

---

### Task 4: Lint, type-check, full test pass, and commit

**Type:** backend
**Estimated scope:** small
**Dependencies:** Tasks 1–3

**Description:**
Run the full validation sequence and confirm all checks pass:

```bash
ruff check --fix . && ruff format . && mypy src/ && pytest tests/unit/ -v
```

Fix any mypy or lint issues surfaced by the new code. Commit with message:

```
feat(wiki): inject wiki snapshot context into chapter and scene generation
```

**Acceptance Criteria:**

- [ ] `ruff check --fix .` exits 0 with no errors.
- [ ] `mypy src/` exits 0 (notes are acceptable; errors are not).
- [ ] `pytest tests/unit/` passes all tests (704+ passing, no regressions).
- [ ] The feature is committed on `development` branch.

**Key Files:**

- All files modified in Tasks 1–3.

---

## Deferred: Track B — Tool-calling / dynamic wiki search

See [ADR 013](../adr/013-wiki-context-injection-vs-tool-calling.md) for the rationale. Track B (adding `generate_with_tools` to `ModelProvider` and wiring wiki-search as a live tool the LLM can call during inference) is deferred until:

1. Track A is validated in production use.
2. A function-calling capable model is confirmed available in the deployment environment.

Track B tasks when resumed:
- Add `generate_with_tools(messages, tools, model_config, ...)` to `ModelProvider` interface.
- Implement tool-dispatch loop in `OpenAIAsyncProvider` (call → inspect `tool_calls` → execute → append result → recurse).
- Define `wiki_search` as an OpenAI-format tool schema backed by `wiki_search.cmd_semantic()`.
- Wire into `ChapterWriterAgent._draft_direct()`.
