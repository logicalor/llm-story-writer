---
date: "2026-04-25"
issue: 163
pr: 174
category: instruction
targets:
  - ".github/notes/gotchas.md"
  - ".github/agents/test-writer.agent.md"
severity: minor
status: archived
---

## Testing Textual apps with `@work(thread=True)` workers

### Finding

Textual apps that run blocking code in `@work(thread=True)` workers require a specific
test pattern. Three issues arise if the pattern is not followed:

1. **Worker fires before assertions** — `pilot.pause()` is needed to yield control back
   to the event loop so the worker can start, run, and post results before the test asserts.
2. **Real pipeline executes** — without mocking `_run_pipeline`, the test makes real LLM
   calls, hangs indefinitely, or raises configuration errors.
3. **`app.run_test()` must be used as an async context manager** — using `app.run()`
   blocks the test thread; `run_test()` returns a pilot that drives the app without
   blocking.

Correct pattern:

```python
@pytest.mark.asyncio
async def test_my_textual_feature(monkeypatch):
    async def fake_pipeline(*args, **kwargs):
        pass  # prevent real pipeline from executing

    monkeypatch.setattr(
        "src.presentation.tui.app.MyApp._run_pipeline", fake_pipeline
    )

    app = MyApp(story_name="test-story")
    async with app.run_test() as pilot:
        await pilot.pause()  # allow worker to start
        # ... interact and assert
        await pilot.pause()  # allow any post-interaction updates
        assert app.query_one("#status").renderable == "Complete"
```

Key rules:
- `monkeypatch` `_run_pipeline` (or equivalent) to prevent real execution.
- Use `async with app.run_test() as pilot` — not `app.run()`.
- Use `await pilot.pause()` after any action that triggers a worker or reactive update.
- Multiple `pause()` calls may be needed for multi-step interactions.

### Observation

The `pilot.pause()` requirement is not obvious from Textual's documentation when you first
encounter it. Missing it produces flaky tests: the assertion fires before the worker thread
has posted its result to the DOM, failing intermittently depending on machine speed.

### Suggested Improvement

1. Add gotcha #026 to `.github/notes/gotchas.md` under "UI / Textual" (new section).
2. Add a Textual-specific testing bullet to the Test Writer agent.

### Action Taken

Applied: Added gotcha #026 to `.github/notes/gotchas.md` and added Textual test guidance
to test-writer.agent.md.
