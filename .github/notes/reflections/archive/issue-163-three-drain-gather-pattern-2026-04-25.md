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

## Three-drain `asyncio.gather()` pattern for concurrent bus consumption with guaranteed closure

### Finding

When a pipeline function must: (a) run the pipeline, (b) consume two async queues
(token stream + wiki context), and (c) guarantee both buses are closed on exit, a naïve
sequential approach leaves one queue unconsumed if the other raises. The three-drain
`asyncio.gather()` pattern solves this:

```python
async def _pipeline_with_close(self) -> None:
    try:
        await run_pipeline(...)
    finally:
        self._bus.close()
        self._wiki_bus.close()

async def _drain_tokens(self) -> None:
    async for token in self._bus:
        self._update_display(token)

async def _drain_wiki(self) -> None:
    async for item in self._wiki_bus:
        self._update_wiki(item)

# In the worker:
await asyncio.gather(
    self._pipeline_with_close(),
    self._drain_tokens(),
    self._drain_wiki(),
)
```

`_pipeline_with_close` closes both buses in its `finally` block — this signals both drain
coroutines to exit their `async for` loops regardless of whether the pipeline succeeded or
raised. `asyncio.gather()` runs all three concurrently, so neither drain blocks the pipeline
and neither bus backs up.

### Observation

The key invariant is **close-in-finally, not close-on-success**. If `bus.close()` is called
only on the success path, a raised exception leaves the drain coroutines blocked forever
waiting for a sentinel that never arrives. The three-drain pattern ensures both buses
terminate regardless of pipeline outcome.

This generalises to any N producers / M consumers where the producer must signal EOF to all
consumers on exit: close all output channels in the finally block of the producer wrapper.

### Suggested Improvement

Add gotcha #025 to `.github/notes/gotchas.md` under "Async / Threading".

### Action Taken

Applied: Added gotcha #025 to `.github/notes/gotchas.md`.
