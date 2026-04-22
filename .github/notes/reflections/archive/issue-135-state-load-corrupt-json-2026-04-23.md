---
date: "2026-04-23"
issue: 135
pr: 142
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## `_load_story_state` returns `{}` for corrupt JSON — silent state clobber

### Finding

During issue #135 (PR #142, `feat/issue-135-scene-writer-generate-chapter`), the original `_load_story_state` implementation in `scene_writer.py` caught `json.JSONDecodeError` and fell through without returning — effectively returning `None` implicitly, which callers treated as an empty dict via default merge. The result was that a corrupt `state.json` silently became an empty state, and any subsequent `_set_nested` / `_write_state_atomic` call would overwrite the entire state file with only the new key, destroying all prior chapters and metadata. The bug was caught during code review; the PR fixed it by calling `_error()` on `JSONDecodeError`, which exits with code 1 before any write occurs.

### Observation

The "validate at system boundaries" rule in the project conventions addresses input validation at CLI entry points, not internal state-loading helpers. The Coder has no specific guidance about state persistence helpers that read critical JSON files (story state, chapter state). The failure mode — catch the parse error, return empty dict, continue as normal — is an attractive pattern because it mirrors the "file doesn't exist → return {}" case just above it. But the two cases are not symmetric: a missing file is expected (first run); a corrupt file is a data integrity failure that must surface immediately.

### Suggested Improvement

Add a named guidance block for story state loading to the Coder's "Code Patterns" section:

```markdown
**Story state JSON loading:** When implementing `_load_story_state` helpers (or any function that reads `state.json` / chapter state files), treat `json.JSONDecodeError` as a fatal error — call `_error()` and exit. Never catch a JSON parse error and return `{}` or any other fallback value. Missing file (`state_path.exists() == False`) is expected on first run and warrants an empty-dict return; corrupt file is a data integrity failure and must surface immediately. Returning `{}` for a corrupt file silently clobbers all existing story progress on the next write.
```

### Action Taken

Applied: added "Story state JSON loading" named block to the Code Patterns section of `.github/agents/coder.agent.md`, after the existing "TypeScript `data` parameter type" block.
