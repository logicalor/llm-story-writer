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

### 005 — `scene-writer assemble-chapter`: implicit savepoint at `chapter_{N}/chapter_content`

**Source:** issue #27, PR #87 (original); updated PR #153
**Severity:** info

`scene-writer assemble-chapter` **automatically creates a savepoint** at `chapter_{N}/chapter_content` after assembly. No separate `savepoint-mgr save` call is required for the assembled chapter.

To receive the assembled prose inline (e.g. to pass to `quality-reviewer`), pass `includeContent: true`:

```bash
# Assembled chapter saved automatically; prose returned inline:
scene-writer assemble-chapter --story-name my-story --chapter 2 --include-content
```

The response includes `{"chapter_ref": "chapter_2/chapter_content", "savepoint_step": "...", "char_count": N, "scene_count": N, "content": "..."}` when `--include-content` is set. Without it, output is `{"chapter_ref": ..., "char_count": N, "scene_count": N}` and the prose is on disk only.

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

### 014 — asyncio `_closed` flag: set in `close()` but never read in `emit()` or generator entry

**Source:** issue #160, PR #170
**Severity:** warning

Async stream classes that maintain a `_closed` flag commonly set `self._closed = True` inside
`close()` but skip the guard in producer and consumer entry points. This causes two distinct
silent failures:

**Producer entry (`emit()`):**

```python
# Wrong — data silently discarded after close(), no exception raised:
def close(self): self._closed = True
async def emit(self, item): await self._queue.put(item)  # _closed never checked

# Right:
async def emit(self, item):
    if self._closed:
        raise RuntimeError("emit() on closed stream")
    await self._queue.put(item)
```

**Consumer entry (async generator backed by sentinel-terminated queue):**

The `_SENTINEL = object()` approach cleanly terminates the *current* iteration pass, but does
not prevent a second `async for` loop from re-entering the generator and blocking forever
waiting for a second sentinel that will never arrive. Add a closed+empty guard at generator
entry:

```python
# Wrong — re-iterating an exhausted stream blocks forever:
async def __aiter__(self):
    while True:
        item = await self._queue.get()
        if item is _SENTINEL:
            return
        yield item

# Right — guard at generator entry:
async def __aiter__(self):
    if self._closed and self._queue.empty():
        return
    while True:
        item = await self._queue.get()
        if item is _SENTINEL:
            return
        yield item
```

Setting `_closed = True` is necessary but insufficient. Every write-side entry (`emit()`,
`put_nowait()`) and every read-side entry (generator start, consumer loop) must actively read
the flag — not just inherit it.

ChromaDB ID: `gotcha-asyncio-closed-flag-discipline-014`

---

### 015 — asyncio `Future` lazy-init: `resolve()` before `await_decision()` is a no-op → deadlock

**Source:** issue #160, PR #170
**Severity:** critical

Approval gate / one-shot latch patterns that create `asyncio.Future` lazily inside
`await_decision()` fail silently when `resolve()` is called before `await_decision()`:

```python
# Wrong — Future created lazily in await_decision():
class ApprovalGate:
    async def await_decision(self):
        self._future = asyncio.get_event_loop().create_future()
        return await self._future  # waits on a Future nobody else holds

    def resolve(self, result):
        if hasattr(self, "_future"):
            self._future.set_result(result)  # no-op if called before await_decision()
```

When `resolve()` is called before `await_decision()`, `self._future` does not exist yet.
The result is silently dropped. `await_decision()` then creates a new Future and waits
forever — a deadlock with no error signal.

**Fix:** buffer the pending result; return it immediately if already set:

```python
# Right — buffer pending result in __init__:
class ApprovalGate:
    def __init__(self):
        self._pending = None
        self._future: asyncio.Future | None = None

    def resolve(self, result):
        if self._future is not None:
            self._future.set_result(result)
        else:
            self._pending = result  # buffer for pre-await resolution

    async def await_decision(self):
        if self._pending is not None:
            result, self._pending = self._pending, None
            return result
        self._future = asyncio.get_event_loop().create_future()
        try:
            return await self._future
        finally:
            self._future = None
```

This pattern applies to any two-party coordination primitive (gate, latch, promise-style
object) where settle/resolve can occur before the waiter registers.

ChromaDB ID: `gotcha-asyncio-future-lazy-init-deadlock-015`

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

---

### 012 — `save_savepoint`: pass Python objects directly — `str` saves as `.md`, not `.json`

**Source:** issue #154, PR #155
**Severity:** warning

`FilesystemSavepointRepository.save_savepoint(repo, step, data)` branches on `isinstance(data, str)`:

- `str` → written verbatim as `{step}.md` (raw text file)
- non-`str` (list, dict, etc.) → JSON-serialised and written as `{step}.json`

**Wrong:** `_save_savepoint(repo, step, json.dumps(items, indent=2))` — pre-serialising to a
`str` forces `.md` storage; downstream `_load_savepoint` returns a raw JSON string, not the
original Python type. Code that then calls `.items()`, iterates, or subscripts the result
raises a `TypeError` or returns wrong data.

**Right:** `_save_savepoint(repo, step, items)` — pass the Python object directly; the
repository handles serialisation; downstream load returns the original type.

**Test corollary:** Savepoint round-trip tests must assert the **type** of the loaded value,
not only the content:

```python
# Wrong — passes even when loaded value is a JSON string, not a list:
assert saved == items

# Right — catches format regressions immediately:
assert isinstance(saved, list)
assert saved == items
```

ChromaDB ID: `gotcha-savepoint-str-vs-object-format-012`

---

## Agent Workflows

### 013 — Chunked outline generation: must explicitly concatenate `data.chunk_outline` values — no tool auto-merges

**Source:** issue #156, PR #157
**Severity:** warning

`outline-generator expand-chapter` writes each chunk to a savepoint (`outline_chunk_{start}_{end}`) and returns JSON for that chunk only. There is **no tool or pipeline step that auto-merges chunks** into a single consolidated string.

After the last `expand-chapter` call, the agent must explicitly:
1. Collect all `data.chunk_outline` values in chapter order (as extracted during the loop).
2. Concatenate them with `\n\n` separators.
3. Store the result as the outline return value (e.g. `merged_outline` / `current_outline`).

Skipping this yields an empty `story-state field outline` after the orchestrator writes the return value. Failure cascades silently:
- `story-planner` arc analysis fabricates ratings (no outline text to evaluate).
- `chapter-outline-expander` (Phase 7a) expands chapters without approved synopsis context.
- Validation guards fire only when the downstream consumer reads the empty field — after at least one subagent dispatch overhead and potentially after an irreversible state write.

The `expand-chapter` tool calls all succeed with no error signal — the failure is invisible until downstream consumers read the empty field.

```text
# Required consolidation step (conceptual):
# After ALL expand-chapter calls complete:
# merged_outline = "\n\n".join(all data.chunk_outline values in chapter order)
# current_outline = merged_outline
# Return current_outline to the orchestrator
```

ChromaDB ID: `gotcha-chunked-outline-consolidation-no-auto-merge-013`

---

## Story Storage

### 016 — Story state file is `state.json` — not `story_state.json`

**Source:** issue #161, PR #171
**Severity:** warning

All story directories in this repository store state in **`state.json`**, not `story_state.json`.
Verified storage locations:

- `stories/test_story/state.json`
- `stories/test-story/state.json`
- `stories/the-silence-between-stars/state.json`

A new module that constructs the path `story_state.json` will silently receive an empty result
when the file is missing — the typical file-loading fallback (`return ""` / `return {}`) makes
the mismatch invisible at runtime. The pipeline then proceeds with an empty story concept and
produces no error until downstream phases fail.

**Right:** load from `story_dir / "state.json"` — consistent with all existing tools.
**Wrong:** `story_dir / "story_state.json"` — no such file exists in any story directory.

ChromaDB ID: `gotcha-story-state-filename-convention-016`

---

### 017 — `src/presentation/` modules must define `_STORIES_DIR` as a `__file__`-anchored constant

**Source:** issue #161, PR #171
**Severity:** warning

`src/tools/_io.py` defines `STORIES_DIR` using an anchor derived from `__file__`:

```python
PROJECT_ROOT = Path(__file__).resolve().parents[2]
STORIES_DIR = Path(os.environ.get("STORIES_DIR", str(PROJECT_ROOT / "stories")))
```

Modules in `src/presentation/` are in a different architectural layer and should **not** import
directly from `src/tools/_io.py`. Instead, define an equivalent module-level constant using the
same `__file__`-anchored pattern:

```python
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_STORIES_DIR = Path(os.environ.get("STORIES_DIR", str(_PROJECT_ROOT / "stories")))
```

**Wrong:** bare `Path("stories") / story_name` — resolves against the process CWD. Silently
targets the wrong location when invoked from any directory other than the project root (CI,
systemd, test subdirectory). The real project tree gets written into during test runs because
pytest runs from the project root and mocks are not always complete.

**Right:** `_STORIES_DIR / story_name` — anchored to the file's own location, independent of
process CWD. Overridable via `STORIES_DIR` environment variable for tests.

Relation to gotcha #011: #011 covers `src/tools/` modules and `STORIES_DIR` testing patterns;
this entry extends the convention to `src/presentation/` and other non-tools layers.

ChromaDB ID: `gotcha-stories-dir-presentation-layer-017`

---

### 018 — `_validate_story_name()` is required in all Python entry points accepting user-supplied story names

**Source:** issue #161, PR #171
**Severity:** warning

`_validate_story_name()` from `src/tools/_io.py` is the canonical story-name security guard. It
performs two critical operations on every entry: (1) path traversal rejection — any name
containing `../` or similar sequences raises `SystemExit`; (2) normalisation — converts the name
to the kebab-case form used as the story directory name.

**Every existing story-facing tool** calls this function immediately upon receiving a `story_name`
argument (`savepoint_manager.py`, `story_state.py`, `wiki_maintainer.py`, `critique_runner.py`,
etc.). Omitting the call in a new module creates a path traversal surface (CWE-22) where a
maliciously crafted story name can escape the `STORIES_DIR` base.

```python
# Right — canonical story-name guard at entry point:
from src.tools._io import _validate_story_name

def run_pipeline(story_name: str, ...) -> PipelineState:
    story_dir = _validate_story_name(story_name)  # raises on traversal; normalises to kebab-case
    ...
```

**Test isolation:** use `monkeypatch.setattr(module, "_validate_story_name", lambda n: tmp_path / n)`
or patch the import; the guard prevents the function from resolving real disk paths in unit tests.

ChromaDB ID: `gotcha-validate-story-name-entry-point-requirement-018`

---

## Python Patterns

### 019 — Use `isinstance()` for type dispatch — never `type(x).__name__` string comparison

**Source:** issue #161, PR #171
**Severity:** warning

`type(x).__name__ == "ClassName"` is a fragile type-dispatch pattern with two silent failure modes:

1. **Subclass bypass** — a subclass of `ClassName` has a different `__name__` (the subclass name),
   so the check returns `False` for a valid subclass instance. The caller falls back silently to
   unexpected behaviour with no error signal.
2. **Rename breakage** — if `ClassName` is renamed during a refactor, the comparison continues to
   compile and run but always returns `False`, silently disabling every branch that depended on it.

`isinstance()` is immune to both:

```python
# Wrong — breaks on subclass or rename:
batch_mode = type(gate).__name__ == "NullApprovalGate"

# Right — semantically correct, survives subclass and rename:
from src.presentation.pipeline_primitives import NullApprovalGate
batch_mode = isinstance(gate, NullApprovalGate)
```

This applies to any conditional that uses a class as a discriminant: gate/mode detection, dispatch
tables, factory branches. The pattern generates no lint warning and no type error — it fails only
in production when the type hierarchy changes.

ChromaDB ID: `gotcha-isinstance-not-type-name-019`
