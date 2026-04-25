---
date: "2026-04-25"
issue: 183
pr: 195
category: instruction
targets:
  - ".github/notes/gotchas.md"
severity: minor
status: archived
---

## asyncio.to_thread with sync tool scripts: wrap in try/except to contain raw exceptions

### Finding

PR #195 (issue #183) called `asyncio.to_thread(update_wiki_from_chapter, ...)` inside
`WikiMaintainerAgent.run()`. Review finding S-W-01 (Warning) flagged that the call had no
exception handling. Sync tool scripts raise `ValueError`, `RuntimeError`, and `SystemExit`
directly on failure — these raw exceptions would propagate out of the `await asyncio.to_thread`
call unmodified and potentially kill the outer pipeline loop.

The fix added `try/except Exception` around the `await asyncio.to_thread` call, logging the
exception and raising a domain error with story/chapter context.

### Observation

`asyncio.to_thread` faithfully re-raises any exception raised in the worker thread, including
`ValueError`, `RuntimeError`, and `SystemExit` from sync CLI-style tool scripts. Sync scripts
are designed to be called from `if __name__ == "__main__"` contexts where these exceptions
terminate the process — the same behaviour is destructive when the thread is part of a
chapter-generation loop. A missed `except` lets one wiki-update failure abort the entire
multi-chapter pipeline run.

### Suggested Improvement

Add a gotcha entry to `.github/notes/gotchas.md` documenting the exception-wrapping requirement
when using `asyncio.to_thread` with sync tool scripts.

### Action Taken

Applied: Added gotcha #030 to `.github/notes/gotchas.md` under the "Async / Threading" section.
