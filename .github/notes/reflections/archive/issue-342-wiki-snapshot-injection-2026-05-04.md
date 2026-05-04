---
date: "2026-05-04"
issue: 342
pr: 343
category: instruction
targets:
  - ".github/notes/gotchas.md"
  - ".github/notes/architecture.md"
severity: minor
---

## Wiki snapshot injection pattern and `get_snapshot()` never-raises contract

### Finding

Issue #342 established `get_snapshot()` as the standard Python API for injecting wiki context
into prose generation agents (`ChapterWriterAgent.run()` and `_run_scene_pipeline()`). Two
patterns emerged that are worth documenting for future agents that follow the same injection
model:

1. **`get_snapshot()` never raises.** The function catches `(Exception, SystemExit)` and returns
   `None`. Call sites do not need a `try/except` for safety. If the wiki is absent, the ChromaDB
   collection is empty, or any internal error occurs, `None` is returned and the caller falls back
   to its existing context. An outer `try/except` is only appropriate when the caller wants to
   emit user-visible diagnostic feedback on failure — as `ChapterWriterAgent` does via the
   `TokenStreamBus`.

2. **Standard injection pattern for prose agents.** After building the flat-sheet `base_context`,
   check whether `wiki/` exists, call `get_snapshot()` with the chapter/scene outline as the
   query, and replace `base_context` only when the result is non-`None`. This is the canonical
   fallback contract: wiki present + non-empty → use snapshot; otherwise → use flat-sheet context.

### Observation

These two facts — the never-raises guarantee and the fallback injection pattern — are not captured
anywhere in the shared knowledge base. Future implementers adding wiki context to new agents
(e.g. `QualityReviewerAgent`, `ConsistencyCheckerAgent`) will rediscover them from source code
unless they are documented.

The never-raises contract is particularly important: without knowing about it, a future coder may
wrap `get_snapshot()` in a `try/except` defensively, obscuring the actual intent or suppressing
real errors from higher-level logic.

### Suggested Improvement

1. Add gotcha #053 to `.github/notes/gotchas.md` under a new "Wiki / Context Injection" section:
   the `get_snapshot()` never-raises contract and the standard injection pattern.

2. Add a short note to `.github/notes/architecture.md` under "Pipeline Flow" documenting that
   the Python `ChapterWriterAgent` (introduced in issue #342) injects a wiki snapshot as
   `base_context` before each chapter and scene prompt.

### Action Taken

Applied:
- Gotcha #053 added to `.github/notes/gotchas.md` (new "Wiki / Context Injection" section).
- Architecture note updated in `.github/notes/architecture.md` — chapter generation loop step
  now documents wiki snapshot injection.
- Reflection embedded into ChromaDB `reflections` collection.
