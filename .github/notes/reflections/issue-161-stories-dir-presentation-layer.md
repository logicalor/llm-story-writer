---
date: "2026-04-25"
issue: 161
pr: 171
category: instruction
targets:
  - ".github/notes/gotchas.md"
severity: minor
status: archived
---

## `src/presentation/` modules must define `_STORIES_DIR` with `__file__`-anchored path

### Finding

PR #171's `src/presentation/orchestrator.py` used bare `Path("stories") / story_name` at four
locations (`_savepoint_path()`, `_load_story_prompt()`, `_continue_pipeline()`, and a `mkdir`
call). This resolves against the process CWD at runtime. An invocation from any directory other
than the project root silently targets the wrong location. All three models identified this
unanimously (U-W-01). The existing tests passed accidentally because pytest runs from the project
root and the critical paths were mocked, with one unintended side-effect: the `mkdir` call created
a real `stories/test-story/savepoints/` directory during test runs.

The established project convention in `src/tools/_io.py` uses:

```python
PROJECT_ROOT = Path(__file__).resolve().parents[N]
STORIES_DIR = Path(os.environ.get("STORIES_DIR", str(PROJECT_ROOT / "stories")))
```

The presentation layer should define its own module-level constant following this same pattern
rather than importing from `src/tools/_io.py` (a cross-layer import).

### Observation

Gotcha entry #011 documents the `STORIES_DIR` convention for `src/tools/` modules but explicitly
scopes itself to tool scripts. As the Python-native migration adds more modules in
`src/presentation/`, each is at risk of introducing the CWD-relative path anti-pattern unless the
convention is extended to cover the presentation layer explicitly.

### Suggested Improvement

Add gotcha entry #017 to `.github/notes/gotchas.md` under `## Story Storage` documenting that
`src/presentation/` modules must define a module-level `_STORIES_DIR` constant following the
`src/tools/_io.py` pattern, and must never use bare `Path("stories")`.

### Action Taken

Applied: Added gotcha entry #017 (`gotcha-stories-dir-presentation-layer-017`) to
`.github/notes/gotchas.md` under `## Story Storage`.
