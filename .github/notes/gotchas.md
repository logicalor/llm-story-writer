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

---

## CLI / Entry Points

### 020 — `pyproject.toml [build-system]`: correct backend string is `setuptools.build_meta`

**Source:** issue #162, PR #172
**Severity:** critical

The PEP 517 build backend for setuptools is **`setuptools.build_meta`** — not `setuptools.backends.legacy:build` or any other variant. The invalid string does not fail at `pyproject.toml` parse time; it fails at `pip install` / `python -m build` time with a confusing `ModuleNotFoundError` or `BackendUnavailable` error that does not name the pyproject field.

**Wrong:**
```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.backends.legacy:build"
```

**Right:**
```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
```

The correct `build-backend` string matches the Python import path of the backend module (`setuptools.build_meta`). The string `setuptools.backends.legacy:build` is a fabrication — `setuptools.backends` is not a valid module path.

ChromaDB ID: `gotcha-pyproject-build-backend-020`

---

### 021 — Headless CLI pipeline invocation: use `NullApprovalGate` + `TokenStreamBus` + `WikiContextBus`

**Source:** issue #162, PR #172
**Severity:** info

The canonical pattern for invoking `run_pipeline()` or `resume_pipeline()` from a non-interactive CLI context (batch mode, console script, CI) is:

```python
import asyncio
from src.presentation.pipeline_primitives import (
    NullApprovalGate,
    TokenStreamBus,
    WikiContextBus,
    run_pipeline,
)

gate = NullApprovalGate()
bus = TokenStreamBus()
wiki_bus = WikiContextBus()
asyncio.run(run_pipeline(story, gate, bus, wiki_bus))
```

- `NullApprovalGate` auto-approves all quality gates without human interaction.
- `TokenStreamBus` and `WikiContextBus` are unbounded asyncio queues. Safe to create and discard in headless mode — both are closed in the pipeline's `finally` block.
- Do not wire `bus` or `wiki_bus` to any downstream consumer in headless mode; the queues drain into the GC on pipeline exit.

For TUI/interactive mode, replace `NullApprovalGate` with an interactive approval gate and wire `bus` / `wiki_bus` to the display layer.

ChromaDB ID: `gotcha-null-approval-gate-headless-pipeline-021`

---

### 022 — `src/presentation/cli/main.py`: requires dual `sys.path` bootstrap for editable installs

**Source:** issue #162, PR #172
**Severity:** warning

When a package is installed in editable mode (`pip install -e .`) and invoked via a `console_scripts` entry point, Python resolves the entry module through the installed `.pth` file — but deep relative imports inside lazy-loaded functions (`_cmd_run`, `_cmd_tui`, etc.) can fail with `ModuleNotFoundError` if neither the project root nor `src/` is on `sys.path` at import time.

Insert these four lines at the **top of `src/presentation/cli/main.py`**, before any local imports:

```python
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[3]
_src_dir = _project_root / "src"
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))
```

Without this, the `story-writer` console script fails when run from any directory other than the project root. The bootstrap is **idempotent** (the `not in sys.path` guards prevent duplicates on repeated imports) and is safe for both editable and installed releases.

Relation to gotcha #007: #007 covers `sys.path.insert` in **test files** for resolving `src/` imports; this entry covers the production CLI entry module bootstrap for editable console scripts.

ChromaDB ID: `gotcha-cli-main-sys-path-bootstrap-022`

---

## UI / Textual

### 023 — Cross-thread asyncio bridge: use `loop.call_soon_threadsafe()` to resolve Futures from TUI thread

**Source:** issue #163, PR #174
**Severity:** warning

When a Textual app runs a pipeline in a `@work(thread=True)` worker and needs to send a UI
decision (e.g. approval gate) back to the worker's `asyncio.run()` event loop, calling
`future.set_result()` directly from the Textual event-loop thread is **thread-unsafe** and
raises `RuntimeError: Future is attached to a different loop` or causes undefined behaviour.

The correct pattern uses `loop.call_soon_threadsafe()`:

```python
class TUIApprovalGate:
    def __init__(self):
        # Capture the worker's event loop BEFORE asyncio.run() replaces it:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._future: asyncio.Future | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Called from the worker thread after asyncio.get_event_loop()."""
        self._loop = loop

    def resolve_from_ui(self, decision: bool) -> None:
        """Called from the Textual (UI) thread — must NOT touch the future directly."""
        if self._future is not None and self._loop is not None:
            self._loop.call_soon_threadsafe(self._future.set_result, decision)

    async def await_decision(self) -> bool:
        self._future = asyncio.get_event_loop().create_future()
        try:
            return await self._future
        finally:
            self._future = None
```

`bind_loop()` captures the pipeline's event loop from the worker thread before `asyncio.run()`
is entered. `call_soon_threadsafe` enqueues the `set_result` callback onto the correct loop
from any external thread.

**Anti-patterns:**
- `future.set_result(v)` from the UI thread — thread-unsafe, `RuntimeError` on CPython ≥ 3.10
- `loop.run_until_complete(...)` from the UI thread — deadlock (loop already running)
- Calling `asyncio.get_event_loop()` inside `resolve_from_ui` — may return Textual's loop, not the worker's loop

**Generalises to:** any architecture where a TUI (Textual, curses, tkinter) must inject results
into a separately-running `asyncio.run()` worker loop.

ChromaDB ID: `gotcha-asyncio-cross-thread-bridge-023`

---

### 024 — `RichLog` defaults to `markup=True`; use `markup=False` for LLM/user-generated content

**Source:** issue #163, PR #174
**Severity:** warning

Textual's `RichLog` widget defaults to `markup=True`, which interprets Rich markup syntax
(`[bold]`, `[red]`, `[link=…]`) in every string written with `.write()`. LLM-generated content
routinely contains square brackets — citation numbers `[1]`, Markdown footnotes `[^1]`,
enumeration prefixes `[a]`, partial HTML/tags — that Rich parses as markup. When Rich encounters
an unrecognised or unclosed tag it raises `MarkupError` or silently drops text, corrupting the
streaming display.

```python
# Wrong — default markup=True corrupts any LLM token containing []:
log = RichLog()

# Right — markup=False passes all content as plain text:
log = RichLog(markup=False)
```

The bug is invisible in unit tests that use short mock token strings. It only manifests in
integration or end-to-end runs with real LLM output — first encountered when a story run
containing citation brackets `[1]` silently dropped the surrounding sentence.

**Wider principle:** never enable `markup=True` on any display widget that renders content
outside the application's control (user input, LLM tokens, file content, web data).

ChromaDB ID: `gotcha-richlog-markup-false-user-content-024`

---

### 025 — Three-drain `asyncio.gather()` pattern: close buses in `finally`, drain concurrently

**Source:** issue #163, PR #174
**Severity:** info

When a pipeline coroutine produces output on two async buses (`TokenStreamBus`, `WikiContextBus`)
and a TUI worker must consume both while the pipeline runs, a naïve sequential approach
(`await pipeline(); async for token in bus: ...`) leaves one bus unconsumed if the pipeline raises.
The three-drain `asyncio.gather()` pattern solves this with a single invariant: **close all buses
in a `finally` block** so all drain coroutines receive their termination signal regardless of
outcome.

```python
async def _pipeline_with_close(self) -> None:
    """Run pipeline; always close both buses on exit."""
    try:
        await run_pipeline(self._story_name, self._gate, self._bus, self._wiki_bus)
    finally:
        self._bus.close()
        self._wiki_bus.close()

async def _drain_tokens(self) -> None:
    async for token in self._bus:
        self._log.write(token)

async def _drain_wiki(self) -> None:
    async for item in self._wiki_bus:
        self._wiki_panel.update(item)

async def _run_all(self) -> None:
    await asyncio.gather(
        self._pipeline_with_close(),
        self._drain_tokens(),
        self._drain_wiki(),
    )
```

`asyncio.gather()` runs all three coroutines concurrently. When the pipeline exits (success or
exception), `finally` closes both buses. The drain coroutines see the sentinel and exit their
`async for` loops. `asyncio.gather()` waits for all three to complete before returning.

**Key invariant:** call `bus.close()` in `finally`, **not** after `await run_pipeline()`. If
the close is only on the success path, an exception leaves all drain coroutines blocked forever.

**Scales to N buses / M producers:** wrap each producer in a `_produce_with_close()` coroutine
that closes its own output channels in `finally`; gather all producers and consumers together.

ChromaDB ID: `gotcha-asyncio-three-drain-gather-pattern-025`

---

### 026 — Testing Textual apps with `@work(thread=True)` workers: mock worker, use `pilot.pause()`

**Source:** issue #163, PR #174
**Severity:** info

Textual apps that run blocking work in `@work(thread=True)` workers require three specific
test practices:

**1. Mock `_run_pipeline` (or equivalent) to prevent real execution:**

```python
async def fake_run(*args, **kwargs):
    pass  # do nothing — worker exits immediately

monkeypatch.setattr(
    "src.presentation.tui.app.StoryWriterApp._run_pipeline", fake_run
)
```

Without this, the test either hangs (waiting for LLM) or raises configuration errors.

**2. Use `app.run_test()` as an async context manager — never `app.run()`:**

```python
app = StoryWriterApp(story_name="test-story")
async with app.run_test() as pilot:
    ...
```

`app.run()` blocks the calling thread; `run_test()` returns a `Pilot` that drives the app
through the test event loop without blocking.

**3. Use `await pilot.pause()` after any worker-triggering action:**

```python
async with app.run_test() as pilot:
    await pilot.pause()          # allow mount/compose lifecycle
    await pilot.click("#start")  # triggers @work(thread=True) worker
    await pilot.pause()          # yield for worker to start and post results
    assert app.query_one("#status").renderable == "Running"
    await pilot.pause()          # yield for worker to complete
    assert app.query_one("#status").renderable == "Complete"
```

`pilot.pause()` yields control back to the event loop, allowing pending callbacks, reactive
updates, and worker-posted messages to process. Multiple `pause()` calls may be needed for
multi-step interactions. Missing a `pause()` produces flaky tests: the assertion fires before
the worker has posted its result to the DOM.

**Note:** `@pytest.mark.asyncio` is required; Textual's `run_test()` is an async context manager.

ChromaDB ID: `gotcha-textual-work-thread-testing-026`

---

### 027 — E2E subprocess test story names must be pre-normalized kebab-case

**Source:** issue #165, PR #176
**Severity:** warning

When writing E2E integration tests that seed story data (e.g. `state.json`) and then invoke the
CLI via `subprocess.run`, always pass a story name that is **already in canonical kebab-case**
to both the subprocess and the test fixture. Do **not** rely on the pipeline normalising the name
internally.

**Why:** `run_pipeline()` in `src/presentation/orchestrator.py` calls `_validate_story_name()`
but **discards the return value**. The raw (un-normalised) `story_name` is stored directly in
`PipelineState` and used for all subsequent path operations:

```python
# Wrong — discards normalised form:
_validate_story_name(story_name, STORIES_DIR)
state = PipelineState(story_name=story_name, ...)  # raw name stored
story_dir = STORIES_DIR / story_name               # --> stories/e2e_test_/
```

**Consequence:** If the test seeds `stories/e2e-test/state.json` but passes `--story e2e_test_`,
the pipeline writes to `stories/e2e_test_/` and the assertions check `stories/e2e-test/` —
producing either a `FileNotFoundError` on the seeded state (hard failure) or vacuous assertions
against stale data from a prior run (silent false-pass). Neither failure produces a clear error
message pointing to the name mismatch.

**Right:** Use a name that is already in canonical kebab-case in both the fixture and the CLI
invocation:

```python
STORY_NAME = "e2e-test"           # already kebab-case — no normalisation needed
STORY_DIR  = STORIES_DIR / "e2e-test"

# subprocess:
subprocess.run(["python", "-m", "src...", "--story", STORY_NAME], ...)
```

**Isolation:** Combine with `tmp_path` and the `STORIES_DIR` env var to prevent
cross-test contamination and real-data loss:

```python
@pytest.fixture(scope="session")
def e2e_story_dir(tmp_path_factory: pytest.TempPathFactory):
    base = tmp_path_factory.mktemp("stories")
    story_dir = base / "e2e-test"
    story_dir.mkdir(parents=True)
    # seed state.json ...
    yield story_dir
    # tmp_path dirs are cleaned automatically — no shutil.rmtree needed

# In the test:
result = subprocess.run(
    [..., "--story", "e2e-test"],
    env={**os.environ, "STORIES_DIR": str(story_dir.parent)},
    ...
)
```

This pattern also prevents deletion of a developer's real story named `"e2e-test"` and avoids
parallel-runner path conflicts.

ChromaDB ID: `gotcha-e2e-test-story-name-kebab-case-027`

---

### 028 — `story_dir.parent` is idiomatic for recovering `stories_dir` inside helper functions

**Source:** issue #182, PR #194
**Severity:** info

When a helper function receives a validated `story_dir` path (returned by `_validate_story_name()`),
use `story_dir.parent` to recover the `stories_dir` root — do **not** re-read `STORIES_DIR` from
the environment or accept a separate `stories_dir` parameter.

`_validate_story_name()` always returns an absolute, normalised `Path`:

```python
# src/tools/_io.py
def _validate_story_name(story_name: str) -> Path:
    ...
    return STORIES_DIR / kebab_name   # absolute: /path/to/stories/my-story
```

So `story_dir.parent` is always `STORIES_DIR`:

```python
# Inside a helper that already has story_dir:
def _list_character_sheets(story_dir: Path) -> list[Path]:
    sheets_dir = story_dir / "characters"
    ...

# Caller — passing stories_dir to a sibling helper:
def cmd_generate(story_name: str) -> None:
    story_dir = _validate_story_name(story_name)      # .../stories/my-story
    stories_dir = story_dir.parent                     # .../stories/
    _generate_sheet(story_dir, stories_dir)            # idiomatic
```

**Why not re-read `STORIES_DIR`?** A second `os.environ.get("STORIES_DIR")` call introduces a
second read point — if the environment changes between calls (rare in production, common in tests
where monkeypatch patches only one binding), the two values diverge silently. `story_dir.parent`
derives `stories_dir` from the already-validated path, guaranteeing consistency.

**Why not add a `stories_dir` parameter?** Adding `stories_dir` to every helper's signature
propagates redundant state and widens the test fixture surface. The parent relationship is an
invariant of `_validate_story_name()`'s contract — exploit it at call sites.

ChromaDB ID: `gotcha-story-dir-parent-stories-dir-028`

---

## Infrastructure / LLM

### 029 — `ModelConfig.host` must be threaded as `base_url` — model name alone is insufficient

**Source:** issue #183, PR #195
**Severity:** critical

When passing a `ModelConfig` into a tool-layer function that calls an LLM, always derive
`base_url` from `model_config.host` and forward it explicitly:

```python
base_url = f"http://{model_config.host}/v1" if model_config.host else None
```

Passing only `model_config.name` causes the LLM call to silently resolve against the default
endpoint (typically `localhost:1234`) — regardless of which model server the story is configured
to use.

**Wrong:**
```python
# Only model name forwarded — base_url silently dropped:
result = await asyncio.to_thread(
    update_wiki_from_chapter,
    story_name, chapter_num, chapter_text,
    model=model_config.name,          # host dropped here
)
```

**Right:**
```python
base_url = f"http://{model_config.host}/v1" if model_config.host else None
result = await asyncio.to_thread(
    update_wiki_from_chapter,
    story_name, chapter_num, chapter_text,
    model=model_config.name,
    base_url=base_url,                # endpoint explicit
)
```

**Why this is hard to catch:** The LLM call succeeds when the default server exists (local dev
with a single LM Studio instance). The bug only manifests in multi-endpoint deployments or
when the default endpoint is offline — producing a silent wrong-endpoint call with no error.

The `base_url` parameter must thread through every intermediate function that forwards the model
argument: `update_wiki_from_chapter` → `_prepare_chapter_update` → `_chat_completion`.

ChromaDB ID: `gotcha-model-config-host-base-url-threading-029`

---

## Async / Threading

### 030 — `asyncio.to_thread` with sync tool scripts: always wrap in `try/except Exception`

**Source:** issue #183, PR #195
**Severity:** warning

`asyncio.to_thread` faithfully re-raises any exception raised in the worker thread. Sync tool
scripts in `src/tools/` are designed for CLI use: they raise `ValueError`, `RuntimeError`, and
`SystemExit` directly on failure. When called via `asyncio.to_thread` inside an async pipeline
loop, these raw exceptions escape into the awaiting coroutine and can abort the entire
multi-chapter run.

**Wrong:**
```python
# Raw exception from sync script escapes — kills chapter loop on first wiki error:
await asyncio.to_thread(update_wiki_from_chapter, story_name, chapter_num, ...)
```

**Right:**
```python
try:
    await asyncio.to_thread(
        update_wiki_from_chapter, story_name, chapter_num, ...
    )
except Exception as exc:
    logger.error(
        "Wiki update failed for story '%s' chapter %d: %s",
        story_name, chapter_num, exc,
    )
    raise WikiUpdateError(
        f"Wiki update failed for chapter {chapter_num}: {exc}"
    ) from exc
```

Re-raise as a domain error with story/chapter context so the outer pipeline loop can handle it
deliberately (log and continue, or abort with a meaningful message) rather than receiving an
undifferentiated `ValueError` or `RuntimeError`.

ChromaDB ID: `gotcha-asyncio-to-thread-sync-exception-wrapping-030`

---

## Testing

### 031 — `_chat_completion` test stubs must declare `base_url: str | None = None`

**Source:** issue #183, PR #195
**Severity:** warning

`_chat_completion` now accepts `base_url: str | None = None` to support multi-endpoint
deployments. Any test stub that patches this function must include `base_url` in its signature,
or production call sites that pass `base_url=some_url` will raise:

```
TypeError: _fake_chat_completion() got an unexpected keyword argument 'base_url'
```

**Wrong:**
```python
def _fake_chat_completion(prompt: str, model: str) -> str:
    return "mocked response"
```

**Right:**
```python
def _fake_chat_completion(
    prompt: str,
    model: str,
    base_url: str | None = None,
) -> str:
    return "mocked response"
```

**Generalisation:** Whenever a shared infrastructure function (`_chat_completion`,
`_generate_text`, `_call_llm`, etc.) gains a new keyword argument, update **every** test stub
that patches that function across the entire test suite. A stub with a fixed signature will
only fail for test paths that actually pass the new kwarg — other tests continue to pass, making
the coverage gap easy to miss in PR review.

ChromaDB ID: `gotcha-chat-completion-stub-base-url-signature-031`

---

## LLM JSON Parsing

### 032 — `data.get("key", {})` null-trap: explicit JSON `null` returns `None`, not the default

**Source:** issue #184, PR #197
**Severity:** warning

When an LLM returns explicit JSON `null` for a field — `{"issues": null}` — Python's `dict.get("issues", [])` returns `None`, **not** `[]`. The default argument only substitutes when the key is **absent**; it is not used when the key is present with a `null` value. Any downstream `.items()`, iteration, or `.get()` call on `None` immediately raises `AttributeError` or `TypeError`.

```python
data = json.loads('{"issues": null}')

# Wrong — returns None when LLM explicitly sets the field to null:
issues = data.get("issues", [])
for item in issues:  # TypeError: 'NoneType' is not iterable
    ...

# Right — `or` coalesces None to the fallback:
issues = data.get("issues") or []
for item in issues:  # safe
    ...
```

The same pattern applies to dict-valued fields:

```python
# Wrong:
summary = data.get("summary", {})
for k, v in summary.items():  # AttributeError on null
    ...

# Right:
summary = data.get("summary") or {}
```

This is a systematic footgun in any code that parses structured LLM JSON output. LLMs routinely set fields they cannot populate to explicit `null` rather than omitting them. Apply `or {}` / `or []` unconditionally to all `.get()` calls on LLM-sourced dicts.

ChromaDB ID: `gotcha-llm-json-null-trap-get-default-032`

---

### 033 — Always `isinstance(data, dict)` after `json.loads()` before calling `.get()`

**Source:** issue #184, PR #197
**Severity:** warning

Valid JSON can parse to a `list`, `int`, `float`, `str`, `bool`, or `None` — not only a `dict`. Code that calls `json.loads()` and immediately calls `.get()` on the result without a type guard crashes on any non-dict payload with `AttributeError: 'list' object has no attribute 'get'`.

LLMs occasionally return a list at the root (e.g. `[{"issue": "..."}]`) when prompted for a dict, or return a plain string when confused. A single unexpected response crashes the entire parser.

```python
# Wrong — crashes on list, string, None, or number payload:
data = json.loads(llm_response)
issues = data.get("issues") or []

# Right — guard before any .get():
data = json.loads(llm_response)
if not isinstance(data, dict):
    raise ValueError(f"Expected dict from LLM, got {type(data).__name__}: {llm_response[:100]}")
issues = data.get("issues") or []
```

Extend the pattern to the section-level fields as well: after extracting a nested value, guard it before iterating:

```python
raw_issues = data.get("issues") or []
if not isinstance(raw_issues, list):
    raw_issues = []
```

ChromaDB ID: `gotcha-llm-json-isinstance-dict-guard-033`

---

### 034 — Non-dict list items in LLM JSON: guard before calling `.get()` on items

**Source:** issue #184, PR #197
**Severity:** warning

When iterating a list of objects extracted from LLM JSON output, the LLM may return strings or other scalar values interleaved with the expected dict objects. Any `.get()` call on a `str` raises `AttributeError: 'str' object has no attribute 'get'`. Neither ruff nor mypy catches this — both see the list as `list[Any]` after `json.loads()`.

```python
# LLM may return: ["fix the imports", {"severity": "warning", "message": "..."}]

# Wrong — crashes on string items:
for item in issues:
    severity = item.get("severity", "info")  # AttributeError for str items

# Right — skip non-dict items:
for item in issues:
    if not isinstance(item, dict):
        continue
    severity = item.get("severity") or "info"
```

This guard is required whenever iterating any list sourced from LLM JSON output, including nested lists inside nested dicts. The LLM mixes types more often when the list is long or the prompt schema is complex.

ChromaDB ID: `gotcha-llm-json-non-dict-list-items-034`

---

## Python Patterns

### 035 — Typed SDK integration: prefer `cast()` over `# type: ignore` for contractually guaranteed types

**Source:** issue #211, PR #217
**Severity:** info

When integrating a typed Python SDK with complex generics (e.g., OpenAI SDK 2.x), mypy may fail to narrow union return types even when the branch is contractually guaranteed by the SDK's documented semantics. Three approaches exist:

| Approach | When to use | Example |
|----------|-------------|---------|
| `cast(TargetType, expr)` | Type is contractually guaranteed by SDK docs or prior branching logic | `cast(AsyncOpenAI, client)` |
| `isinstance(obj, TargetType)` | Type is not guaranteed; you need runtime validation | `isinstance(data, dict)` after `json.loads()` |
| `# type: ignore` | **Avoid** — suppresses all type safety for the line; future regressions pass silently |

**Why `cast()` over `# type: ignore`:** `cast()` documents the developer's intent, preserves downstream type safety, and has no runtime effect. `# type: ignore` removes all checking for that line — a subsequent refactor that changes the expression's type will not be caught. `isinstance()` adds runtime overhead and code clutter when the SDK already contractually guarantees the type.

**Example — OpenAI SDK 2.x streaming vs. non-streaming:**

```python
from typing import cast
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionChunk
from openai._streaming import AsyncStream

client = AsyncOpenAI(base_url=base_url)

# Streaming path — mypy sees `ChatCompletion | AsyncStream[ChatCompletionChunk]`
stream = await client.chat.completions.create(..., stream=True)
stream = cast(AsyncStream[ChatCompletionChunk], stream)
async for chunk in stream:
    choice = chunk.choices[0]
    content = cast(str, choice.delta.content)  # SDK guarantees str for content chunks
    ...

# Non-streaming path
response = await client.chat.completions.create(..., stream=False)
response = cast(ChatCompletion, response)
choice = response.choices[0]
message = cast(str, choice.message.content)   # SDK guarantees str for non-streaming
```

**Rule of thumb:** If the SDK docs state "this field is always a string in this mode", use `cast()`. If the value comes from external/untrusted input, use `isinstance()`.

ChromaDB ID: `gotcha-typed-sdk-cast-pattern-035`

---

## Opencode Configuration

### 036 — opencode.json MCP entry: type `"local"`, merged `command` array, no `cwd`

**Source:** issue #224, PR #225
**Severity:** warning

opencode.json MCP server entries differ from VS Code's `.vscode/mcp.json` format in three ways:

| Field | VS Code mcp.json | opencode.json |
|-------|-----------------|---------------|
| `type` | `"stdio"` | **`"local"`** |
| binary + args | `"command": "uvx"` + `"args": ["chroma-mcp", ...]` | `"command": ["uvx", "chroma-mcp", ...]` (merged array) |
| working dir | `"cwd": "/path"` | **no equivalent** — use relative paths; run opencode from project root |

**Wrong (VS Code form — rejected or silently broken in opencode):**
```json
{
  "type": "stdio",
  "command": "uvx",
  "args": ["chroma-mcp", "--client-type", "persistent"]
}
```

**Right (opencode.json form):**
```json
{
  "type": "local",
  "command": ["uvx", "chroma-mcp", "--client-type", "persistent"],
  "enabled": true
}
```

Relative paths in `command` arguments work correctly when `opencode` is invoked from the project root — the standard invocation pattern.

ChromaDB ID: `gotcha-opencode-mcp-entry-format-036`

---

### 037 — opencode-rules plugin key is `"plugin"` (singular)

**Source:** issue #224, PR #225
**Severity:** warning

The `opencode-rules` package is registered under the **`plugin`** key (singular) in `opencode.json`. Using `"plugins"` (plural) causes the plugin to be silently ignored — no error is raised, but rule files are never loaded.

**Wrong:**
```json
{
  "plugins": ["opencode-rules@latest"]
}
```

**Right:**
```json
{
  "plugin": ["opencode-rules@latest"]
}
```

This affects all tasks that add `.opencode/rules/` files — the rules are inert until the plugin is correctly registered under the singular key.

ChromaDB ID: `gotcha-opencode-rules-plugin-key-singular-037`

---

### 038 — opencode agent `permission` blocks use object-map format, not arrays

**Source:** issue #252, PR #253
**Severity:** warning

Opencode agent `permission.bash`, `permission.task`, and `permission.edit` blocks must use the **object-map** format with explicit defaults and pattern-specific overrides. The array format (listing allowed patterns as a list) is silently accepted by some Opencode versions but is undocumented and unreliable.

**Wrong (array format — undocumented, unreliable):**
```yaml
permission:
  bash:
    - "pytest*"
    - "ruff*"
  task:
    - "Coder"
    - "Test Writer"
```

**Right (object-map format — documented):**
```yaml
permission:
  bash:
    "*": "deny"
    "pytest*": "allow"
    "ruff*": "allow"
  task:
    "*": "deny"
    "coder": "allow"
    "test-writer": "allow"
  tools:
    "chroma/*": true
```

Three additional format rules apply:

1. **`permission.task` values are agent file IDs** — the filename without `.md` (e.g., `"coder"` for `coder.md`), not display names (e.g., not `"Coder"` or `"Code Writer"`). Wrong IDs cause silent dispatch failure.
2. **`tools:` entries use boolean `true`**, not string `"allow"`. String values are silently ignored.
3. **`tools:` sub-keys use 2-space indent; `bash:`, `task:`, `edit:` sub-keys use 4-space indent** relative to the block key. The corpus standard (21 of 24 files) uses this spacing. Do not copy from `orchestrator-v3.md`, `coder.md`, or `sprint-runner.md` — those three files have historically non-standard indentation.

ChromaDB ID: `gotcha-opencode-permission-object-map-format-038`
