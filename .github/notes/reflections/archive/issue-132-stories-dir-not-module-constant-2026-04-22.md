---
date: "2026-04-22"
issue: 132
pr: 136
category: instruction
targets:
  - ".github/notes/gotchas.md"
severity: minor
status: archived
---

## `STORIES_DIR` lives in `src.tools._io`, not in individual tool modules

### Finding

During PR #136, a review finding noted that `critique_runner.py` does not expose `STORIES_DIR`
at module level. The constant is defined in `src/tools/_io.py` (read from the `STORIES_DIR`
environment variable at import time) and consumed via `_validate_story_name`, which is
imported into each tool script.

A test writer attempting `patch("src.tools.critique_runner.STORIES_DIR", tmp_path)` would
silently fail — the patch creates a new attribute on the module that `_validate_story_name`
never reads, so the tool continues targeting the real stories directory. The current test
suite correctly uses subprocess invocation with `env["STORIES_DIR"] = str(tmp_path)`, which
works because the subprocess re-evaluates `_io.STORIES_DIR` at import time in the child process.

### Observation

The `_io.py` shared-constants pattern is established across the tool suite (`story_state.py`,
`character_mgr.py`, etc.), so the same gotcha applies to all tool-targeting tests. A test
writer unaware of the pattern may either patch the wrong binding (creating a silent no-op test)
or unnecessarily patch `_validate_story_name` when the simpler subprocess env-var pattern
would suffice.

Documenting the three valid approaches in `gotchas.md` makes the correct pattern immediately
discoverable.

### Suggested Improvement

**`gotchas.md` — add entry 011 in the Testing section:**

Document the three valid test approaches:
1. Subprocess with `env["STORIES_DIR"] = str(tmp_path)` — standard for CLI integration tests
2. `patch("src.tools._io.STORIES_DIR", ...)` — for in-process unit tests
3. `patch("src.tools.<module>._validate_story_name", ...)` — for overriding validation entirely

Explicitly note that `patch("src.tools.<module>.STORIES_DIR", ...)` is an attribute-error
silent no-op and must not be used.

### Action Taken

Applied: Added gotcha entry 011 to `gotchas.md` under the Testing section.
