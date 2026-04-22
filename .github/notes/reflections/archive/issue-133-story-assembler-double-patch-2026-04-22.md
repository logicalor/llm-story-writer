---
date: "2026-04-22"
issue: 133
pr: 137
category: instruction
targets:
  - ".github/notes/gotchas.md"
severity: minor
status: archived
---

## Double-patch required for modules that re-bind `STORIES_DIR` at import time

### Finding

During PR #137 (`feat/issue-133-generate-handoff-story-assembler`), the new test file
`tests/unit/test_story_assembler_generate_handoff.py` patches both
`src.tools._io.STORIES_DIR` **and** `src.tools.story_assembler.STORIES_DIR` (imported as
`sa`):

```python
monkeypatch.setattr(_io_module, "STORIES_DIR", stories_dir)
monkeypatch.setattr(sa, "STORIES_DIR", stories_dir)
```

This is necessary because `story_assembler.py` does:

```python
from src.tools._io import STORIES_DIR, _validate_story_name
```

This `from … import` statement creates a **module-level binding** `sa.STORIES_DIR` that
captures the value of `_io.STORIES_DIR` at import time. Patching `_io.STORIES_DIR` alone
does not update `sa.STORIES_DIR` — the two are independent name bindings after import.

### Observation

Gotcha entry 011 (from issue #132) documents the `_io.STORIES_DIR` pattern and states that
"individual tool scripts do **not** expose `STORIES_DIR` at module level." However,
`story_assembler.py` is an exception: it explicitly imports `STORIES_DIR` at module level,
making it a re-binding that requires double-patching.

The gap in entry 011 means a test writer following it for `story_assembler` would patch only
`_io_module.STORIES_DIR`, leaving `sa.STORIES_DIR` pointing at the real stories directory and
causing tests to silently use production data.

The general rule: any tool module that does `from src.tools._io import STORIES_DIR` at module
level requires double-patching.

### Suggested Improvement

**`gotchas.md` — extend entry 011** to document the double-patch exception:

- Note that `story_assembler.py` (and any future module that explicitly imports `STORIES_DIR`
  at module level) requires patching **both** the `_io` binding and the module-level binding.
- Add a fourth row to the table and an explicit warning.

### Action Taken

Applied: Extended gotcha entry 011 in `gotchas.md` to document the double-patch exception for
modules that re-bind `STORIES_DIR` at module level.
