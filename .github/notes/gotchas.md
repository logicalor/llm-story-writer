# Gotchas

Known surprises, footguns, and non-obvious behaviours collected from production sessions.
Sourced from reflection notes and review findings. Embedded into the `conventions` ChromaDB collection.

---

## ChromaDB

### 001 — L2 Distance to Similarity: use `1/(1+d)`, not `1-d`

**Source:** issue #16, PR #52
**Severity:** warning

**Wrong:** `score = 1.0 - distance` — L2 distances are unbounded (`[0, ∞)`), produces negative similarity scores.
**Right:** `score = 1.0 / (1.0 + distance)` — correctly maps `[0, ∞)` → `(0, 1]`.

ChromaDB's default metric is L2 (Euclidean), not cosine. The `1 - d` formula only works for cosine distance (bounded `[0, 2]`). Zero distance gives `1.0` (perfect match); large distances approach `0.0`.

ChromaDB ID: `gotcha-chromadb-l2-similarity-formula-001`

---

## Tool CLI Interface

### 002 — `wiki-update append-timeline`: all three fields mandatory

**Source:** issue #27, PR #87
**Severity:** warning

`wiki-update append-timeline` requires **`time`**, **`chapter`**, AND **`description`** — all three are mandatory. Omitting any one raises a validation error. The `chapter` field is easy to overlook because other `wiki-update` subcommands don't require an explicit chapter reference.

```bash
# Correct:
wiki-update append-timeline \
  --story-name my-story \
  --time "Day 3, noon" \
  --chapter 2 \
  --description "Elena discovers the map."
```

ChromaDB ID: `gotcha-wiki-update-timeline-mandatory-fields-002`

---

### 003 — `wiki-lint check-chapter --chapter-text`: must be a real file inside STORIES_DIR

**Source:** issue #27, PR #87
**Severity:** warning

`wiki-lint check-chapter --chapter-text` accepts a **file path**, not inline text. The path must:
1. Point to an existing file (the lint tool reads it from disk).
2. Be inside `STORIES_DIR` (enforced by the `is_relative_to` security check — paths outside the stories directory are rejected).

Workflow: write chapter text to a temp file inside the story directory first, then pass that path to `--chapter-text`. A path to a non-existent file or a path outside `STORIES_DIR` raises a validation error.

```bash
# Correct workflow:
echo "$CHAPTER_TEXT" > stories/my-story/chapters/ch02_draft.txt
wiki-lint check-chapter --story-name my-story --chapter-text stories/my-story/chapters/ch02_draft.txt
```

ChromaDB ID: `gotcha-wiki-lint-chapter-text-path-constraint-003`

---

### 004 — `character-mgr generate-sheet` / `setting-mgr generate-sheet`: storage-only, no LLM call

**Source:** issue #27, PR #87
**Severity:** info

`character-mgr generate-sheet` and `setting-mgr generate-sheet` **write JSON to disk only** — they do not call the LLM to generate content. These are pure storage operations.

To create a new character or setting sheet with LLM-generated content:
1. Make a direct LLM call using the appropriate prompt template (character writer, setting writer) to generate the content.
2. Pass the generated content to `generate-sheet` for persistence.

Assuming `generate-sheet` will auto-fill character/setting fields via LLM results in empty sheets.

ChromaDB ID: `gotcha-character-setting-mgr-storage-only-004`

---

### 005 — `scene-writer assemble-chapter`: no implicit savepoint

**Source:** issue #27, PR #87
**Severity:** warning

`scene-writer assemble-chapter` assembles generated scenes into a chapter file but **does not create a savepoint**. After calling `assemble-chapter`, an explicit `savepoint-mgr save` call is required to checkpoint the story state.

```bash
# After assembling:
scene-writer assemble-chapter --story-name my-story --chapter 2

# Must explicitly save:
savepoint-mgr save --story-name my-story --label "chapter-2-complete"
```

Not calling `savepoint-mgr save` means the assembled chapter cannot be restored from a savepoint. Silent data-loss risk.

ChromaDB ID: `gotcha-scene-writer-assemble-no-savepoint-005`

---

### 010 — `wiki-search`: valid `operation` values are `"semantic"` and `"metadata"` — not `"search"`

**Source:** issue #125, PR #131
**Severity:** warning

`wiki-search` defines its `operation` parameter as `z.enum(["semantic", "metadata"])` in
the TypeScript wrapper. The value `"search"` is **not** in the enum and is rejected by Zod
at runtime with no informative error.

| Value | Use |
|-------|-----|
| `"semantic"` | Natural-language free-text query (default for most wiki lookups) |
| `"metadata"` | Structured field matching (filter by page type, tags, etc.) |

The count parameter key is `nResults`, **not** `limit`.

```
# Wrong (rejected at runtime):
operation: "search", limit: 3

# Right:
operation: "semantic", nResults: 3
```

The contrast: `rag-query` also uses `nResults`. Step 2 wiki lookups and Step 3 RAG queries both
use `nResults` — only the tool name and operation enum differ.

ChromaDB ID: `gotcha-wiki-search-operation-names-010`

---

## URI Parsing

### 006 — Python `urlparse` silently drops URI schemes containing underscores

**Source:** issue #99, PR #101
**Severity:** warning

Python's `urllib.parse.urlparse()` does not accept underscores in URI schemes. RFC 3986 §3.1
restricts scheme characters to `[A-Za-z][A-Za-z0-9+\-.]` — underscores are invalid. `urlparse`
silently returns an empty `.scheme` rather than raising an exception, so `lm_studio://host/path`
and `llama_cpp://host/path` are parsed with scheme `""` and the full string treated as a path.

**Wrong:** `urlparse("lm_studio://host/path").scheme` → `""` (silent failure)
**Right:** Extract the scheme by splitting on `"://"` before calling `urlparse`:

```python
if "://" in value:
    scheme, rest = value.split("://", 1)
else:
    scheme = ""
```

When writing tests for functions that accept custom URI schemes containing underscores, write at
least one positive-path test per supported scheme to guard against silent parsing regressions.

ChromaDB ID: `gotcha-urlparse-underscore-scheme-006`

---

## Testing

### 007 — `sys.path.insert` in tool test files is an established convention, not an anti-pattern

**Source:** issue #103, PR #105
**Severity:** info

Test files for `src/tools/` scripts insert `sys.path.insert(0, str(Path(__file__).parent.parent))`
to resolve `src/application.*` and other package imports. This pattern is **correct and required**
— the project's `pyproject.toml` does NOT configure `pythonpath = ["src"]` under
`[tool.pytest.ini_options]`, so pytest does not add `src/` to `sys.path` automatically.

The pattern appears in 7+ test files across `tests/unit/` and `tests/integration/`. Flagging it
as an anti-pattern is a false positive that misreads the pyproject.toml configuration.

```python
# Required import-resolution bootstrap in src/tools/ test files:
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
```

Because `sys.path.insert` appears before any `from src.*` import, it triggers Ruff rule
**E402 (module-level import not at top of file)**. The project's `pyproject.toml` suppresses
E402 for all files under `tests/` via `[tool.ruff.lint.per-file-ignores]`. If E402 fires
in a test file, verify that the per-file-ignore is in place before investigating import order.

Note: root-level `test_*.py` files (outside `tests/`) are legacy/ad-hoc scripts not registered
in `testpaths = ["tests/unit"]` and are intentionally excluded from the E402 suppression glob.

ChromaDB ID: `gotcha-sys-path-insert-tool-tests-007`

---

## Async / Threading

### 008 — `asyncio.to_thread(path.rglob, pattern)` passes an unevaluated generator

**Source:** issue #111, PR #112
**Severity:** warning

`asyncio.to_thread(path.rglob, pattern)` does **not** offload filesystem I/O to a worker thread.
`path.rglob(pattern)` returns a lazy generator; `to_thread` calls it with no arguments, receives
the generator object, and returns immediately. The generator is iterated later — on the event
loop thread — so the I/O latency lands on the loop regardless of the `to_thread` call.

**Wrong:** `await asyncio.to_thread(path.rglob, pattern)`
**Right:** `await asyncio.to_thread(lambda: list(path.rglob(pattern)))`

The `lambda` forces both creation and full materialisation of the generator inside the worker
thread. The same problem applies to any API that returns a lazy iterator:
`Path.glob`, `os.scandir`, `csv.reader`, `map()`, etc.

ChromaDB ID: `gotcha-asyncio-to-thread-lazy-iterator-008`

---

## Savepoints

### 009 — Stale sibling extension after savepoint format change (.json ↔ .md)

**Source:** issue #111, PR #112
**Severity:** warning

When `save_savepoint` switches format for a step (string → `.md`; structured → `.json`), the
previous extension file persists on disk. If `load_savepoint` applies a priority rule
(`.json` wins over `.md`), a newly written `.md` file is silently ignored because the old
`.json` still exists.

**Fix:** In `save_savepoint`, delete the sibling extension before writing:

```python
# When saving as .md, remove any stale .json:
path.with_suffix(".json").unlink(missing_ok=True)
# When saving as .json, remove any stale .md:
path.with_suffix(".md").unlink(missing_ok=True)
```

This maintains the invariant at write time rather than leaving cleanup to the caller.

ChromaDB ID: `gotcha-savepoint-stale-sibling-extension-009`

---

### 011 — `STORIES_DIR` lives in `src.tools._io`, not in individual tool modules

**Source:** issue #132, PR #136; extended issue #133, PR #137
**Severity:** info

Most tool scripts (`src/tools/critique_runner.py`, `src/tools/story_state.py`, etc.) do
**not** expose `STORIES_DIR` at module level. The constant is defined in `src/tools/_io.py`
and read from the environment at import time:

```python
# src/tools/_io.py
STORIES_DIR = Path(os.environ.get("STORIES_DIR", str(PROJECT_ROOT / "stories")))
```

Each tool imports `_validate_story_name` from `_io`, which uses that constant internally.

**Exception — modules that re-bind `STORIES_DIR` at import time:** `story_assembler.py` does:

```python
from src.tools._io import STORIES_DIR, _validate_story_name
```

This `from … import` creates a **separate module-level binding** `sa.STORIES_DIR` that
captures the value at import time. Patching `_io.STORIES_DIR` alone does **not** update
`sa.STORIES_DIR`. In-process tests for such modules must patch **both** bindings:

```python
monkeypatch.setattr(_io_module, "STORIES_DIR", stories_dir)   # updates _io authority
monkeypatch.setattr(sa, "STORIES_DIR", stories_dir)            # updates captured binding
```

Four valid test approaches:

| Approach | When to use |
|----------|-------------|
| Subprocess with `env["STORIES_DIR"] = str(tmp_path)` | CLI integration tests (standard pattern) |
| `patch("src.tools._io.STORIES_DIR", tmp_path / "stories")` | In-process unit tests for tools that do NOT re-export `STORIES_DIR` |
| Double-patch: `_io.STORIES_DIR` + module-level binding | In-process unit tests for modules that `from src.tools._io import STORIES_DIR` |
| `patch("src.tools.<module>._validate_story_name", ...)` | In-process unit tests overriding validation entirely |

**Wrong:** `patch("src.tools.critique_runner.STORIES_DIR", ...)` — `critique_runner` has no
such attribute; the patch silently creates a new attribute that `_validate_story_name` never
reads, leaving the tool targeting the real stories directory.

ChromaDB ID: `gotcha-stories-dir-not-module-constant-011`
