---
date: "2026-04-25"
issue: 162
pr: 172
category: instruction
targets:
  - ".github/notes/gotchas.md"
severity: minor
status: archived
---

## `src/presentation/cli/main.py` requires dual `sys.path` bootstrap for installed console scripts

### Finding

PR #172 wired `story-writer` as a `console_scripts` entry point in `pyproject.toml`. When the
package is installed in editable mode (`pip install -e .`) and the `story-writer` command is
invoked from any directory other than the project root, lazy imports inside `_cmd_run`,
`_cmd_resume`, and `_cmd_tui` fail with `ModuleNotFoundError` because neither the project root
nor `src/` is guaranteed to be on `sys.path` at import time.

The fix: insert a dual `sys.path` bootstrap at the **top of `src/presentation/cli/main.py`**,
before any local imports:

```python
_project_root = Path(__file__).resolve().parents[3]
_src_dir = _project_root / "src"
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))
```

The `not in sys.path` guards make the bootstrap idempotent — safe for both editable installs and
direct `python -m` invocations.

### Observation

This is a distinct case from gotcha #007 (sys.path.insert in test files), which covers
`tests/unit/` bootstraps for resolving `src/` during pytest. The CLI entry module bootstrap is
a **production-code** concern specific to the `console_scripts` installation mechanism. Without
it, the `story-writer` binary works when run from the project root (where Python's CWD puts
`src/` in scope) but fails in all other contexts, including systemd, CI, and any shell session
started from `~` or `/`.

### Suggested Improvement

Add gotcha entry #022 to `.github/notes/gotchas.md` under `## CLI / Entry Points` documenting
the bootstrap pattern and its relationship to gotcha #007.

### Action Taken

Applied: added gotcha entry #022 (`gotcha-cli-main-sys-path-bootstrap-022`) to
`.github/notes/gotchas.md` under `## CLI / Entry Points`.
