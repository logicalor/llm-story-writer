---
date: "2026-05-03"
issue: 327
pr: 339
category: instruction
targets:
  - ".github/notes/gotchas.md"
severity: minor
---

## upsert_from_source path traversal guard requires PROJECT_ROOT-anchored source files

### Finding

`upsert_from_source` enforces `path.is_relative_to(PROJECT_ROOT)`. Integration tests that create
source files under `tmp_path` (`/tmp/pytest-…`) have all `upsert_from_source` calls rejected
with `ValueError`. Tests must create wiki pages under `PROJECT_ROOT / "stories" / story_name`
and clean up in `finally`.

### Observation

The guard is intentional security behaviour (CWE-22 prevention). Tests must work within it, not
around it. The correct fixture pattern uses a unique story name (uuid suffix) and `shutil.rmtree`
in `finally`. This is distinct from the `STORIES_DIR` env override pattern used for CLI
subprocess tests — direct API callers must use real paths.

### Suggested Improvement

Add gotcha #052 to `gotchas.md` documenting the path traversal guard and the correct fixture
pattern.

### Action Taken

Applied: Added gotcha #052 to `.github/notes/gotchas.md`.
