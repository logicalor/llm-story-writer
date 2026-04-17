---
date: "2026-04-15"
issue: 17
pr: 61
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: active
---

## Coder used `__import__("os")` instead of importing STORIES_DIR from `_io.py`

### Finding

During issue #17 (Build wiki-lint Tool), the Coder defined its own `STORIES_DIR` using `__import__("os").environ.get(...)` instead of importing `STORIES_DIR` from `src/tools/_io.py` like every other tool in the codebase. The `__import__("os")` pattern exists nowhere else in the codebase. The Synthesized Review caught this as a Unanimous Warning.

### Observation

This is the same class of defect as issue #6 (Coder pattern amnesia) — an established pattern (`from src.tools._io import STORIES_DIR`) exists across all 14 other tools but was not carried forward to the new implementation. The proposed Rule 10 (prior-tool review, still pending approval from the issue #6 reflection) would have caught this: reviewing any prior wiki tool would have shown the `_io.py` import pattern.

The `_io.py` module was specifically created (issue #53, PR #55) to centralise `STORIES_DIR`, `_validate_story_name`, and `_atomic_write` — eliminating exactly this kind of drift. The Coder reimplemented what the shared module already provides.

This is the third confirmed instance of the pattern-amnesia class:
- Issue #3: subprocess injection and path traversal patterns not applied → fixed by Rule 9
- Issue #6: atomic writes not applied → proposed Rule 10 (pending)
- Issue #17: shared import pattern not used → additional evidence for Rule 10

### Suggested Improvement

No new rule needed — this is additional supporting evidence for the pending Rule 10 proposal (issue #6 reflection). The fix was applied during the review cycle.

### Action Taken

Recorded as supporting evidence for the pending Rule 10 proposal. No agent changes needed — the review system caught and fixed this in the current PR.
