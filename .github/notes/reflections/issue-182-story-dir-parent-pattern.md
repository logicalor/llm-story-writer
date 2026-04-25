---
date: "2026-04-25"
issue: 182
pr: 194
category: instruction
targets:
  - ".github/notes/gotchas.md"
severity: minor
status: active
---

## `story_dir.parent` is idiomatic for passing `stories_dir` into sheet helper functions

### Finding

In PR #194, the Coder passed `stories_dir` to character-sheet helper functions using
`story_dir.parent` — deriving the parent stories directory from the already-validated `story_dir`
path rather than separately resolving `STORIES_DIR` again or accepting an explicit `stories_dir`
parameter in the module signature.

### Observation

`_validate_story_name()` returns `story_dir` (a `Path` pointing to
`STORIES_DIR / kebab-story-name`). Any helper that needs the `stories_dir` root can recover it
cleanly with `story_dir.parent` — no second environment variable read, no cross-layer import,
no extra parameter in the call chain. The pattern is safe because `_validate_story_name()` always
returns an absolute, normalised path, so `.parent` is always the correct `STORIES_DIR`.

This avoids a category of "double import" bugs where a module reads `STORIES_DIR` from the
environment independently and the two values diverge if the environment changes between calls or
if tests only patch one binding.

### Suggested Improvement

Add an entry to `gotchas.md` documenting `story_dir.parent` as the canonical way to recover
`stories_dir` inside helper functions that already receive a validated `story_dir`.

### Action Taken

Applied: Added gotcha #028 to `.github/notes/gotchas.md` under the "Story Storage" section.
