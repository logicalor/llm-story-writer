---
date: "2026-04-24"
issue: 160
pr: 170
category: instruction
targets:
  - ".github/notes/gotchas.md"
  - ".github/agents/_shared/review-checklist.md"
severity: minor
status: active
---

## Asyncio `_closed` flag: set in `close()` but never checked in `emit()` or generator entry

### Finding

PR #170 introduced two async stream classes (token bus, wiki context bus). All three reviewers independently identified that `emit()` after `close()` silently discarded data because `self._closed` was set to `True` in `close()` but never read inside `emit()`. A second related gap: the async generator iterators lacked a closed+empty guard at entry, which meant re-iterating an exhausted stream blocked indefinitely waiting for a second sentinel that would never arrive.

Both patterns are instances of the same "initialize flag but forget to use it" error: the state is correctly maintained but not checked at the right call sites.

### Observation

Setting `_closed = True` in a `close()` method is necessary but insufficient. Every **write-side** entry point (`emit()`, `put()`, `send()`) must check the flag and raise (or at minimum return early) rather than queuing data into a closed stream. Every **read-side** entry point (async generator start, consumer loop) must check `(self._closed and self._queue.empty())` before entering the blocking await, to prevent blocking re-iteration after stream exhaustion.

This is a recurring pattern in asyncio code because `_closed` guards and queue-based sentinel termination feel like independent mechanisms — but they need to cooperate: the sentinel terminates the current iteration; the `_closed` flag prevents a subsequent re-iteration from blocking.

### Suggested Improvement

1. Add gotcha entry #014 to `.github/notes/gotchas.md` under `## Async / Threading` covering the `_closed` flag discipline for both write and read entry points.
2. Add a review checklist bullet to `.github/agents/_shared/review-checklist.md` Phase 2 General covering asyncio closed-flag and lazy-Future patterns.

### Action Taken

Applied:
- Added gotcha #014 (`gotcha-asyncio-closed-flag-discipline-014`) to `.github/notes/gotchas.md`.
- Added "Asyncio coordination primitives" checklist item to Phase 2 General in `.github/agents/_shared/review-checklist.md`.
