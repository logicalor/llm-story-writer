---
date: "2026-04-25"
issue: 163
pr: 174
category: instruction
targets:
  - ".github/notes/gotchas.md"
severity: minor
status: archived
---

## Cross-thread asyncio bridge: `loop.call_soon_threadsafe()` for approval gate resolution

### Finding

`TUIApprovalGate.resolve_from_ui()` is called from Textual's event-loop thread (a UI button handler)
while the gate's `asyncio.Future` lives on a separate `asyncio.run()` event loop in a background
worker thread. Calling `future.set_result()` directly from the wrong thread causes undefined
behaviour (or a `RuntimeError: Future is attached to a different loop`).

The correct bridge is:

```python
def resolve_from_ui(self, decision: bool) -> None:
    if self._future is not None:
        self._loop.call_soon_threadsafe(self._future.set_result, decision)
```

`self._loop` is captured in `__init__` via `asyncio.get_event_loop()` on the worker thread —
before `asyncio.run()` replaces the running loop — so it refers to the pipeline's loop, not
Textual's loop.

### Observation

This pattern is non-obvious and easy to get wrong. Incorrect implementations either call
`future.set_result()` directly (thread-unsafe) or use `loop.run_until_complete()` (deadlock).
The `call_soon_threadsafe` approach is the correct POSIX-thread-safe callback injection.

The pattern generalises to any architecture where a TUI (Textual, curses, tkinter) shares state
with an `asyncio.run()` worker loop: always capture the worker loop reference before the event
loop is entered, and use `call_soon_threadsafe` to post results from the UI thread.

### Suggested Improvement

Add gotcha #023 to `.github/notes/gotchas.md` under "Async / Threading".

### Action Taken

Applied: Added gotcha #023 to `.github/notes/gotchas.md`.
