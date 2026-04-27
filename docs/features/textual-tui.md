# Textual TUI

> Interactive Textual application for the Python-native story pipeline, with live token streaming, wiki context, and approval gates.

## Overview

Issue #163 adds `StoryWriterApp` in `src/presentation/tui/app.py` as the first interactive front end for the Python-native pipeline. It wraps the existing async orchestrator in a Textual application so operators can watch generation progress, inspect wiki-context activity, and respond to approval gates without dropping back to shell prompts.

The TUI stays presentation-only. It does not reimplement orchestration logic or mutate story state directly. Instead, it launches `run_pipeline()` for fresh runs or `resume_pipeline()` for resumed runs, then bridges three transport primitives into Textual widgets: `ApprovalGate` for human decisions, `TokenStreamBus` for streamed model output, and `WikiContextBus` for wiki-context events.

## User Guide

### Run The TUI

Install the Python dependencies, then launch the app with:

```bash
story-writer tui --story <name>
story-writer tui --story <name> --resume
story-writer tui --story <name> --resume --savepoint <name>
```

Use `--resume` to continue a saved pipeline run through the TUI. Add `--savepoint <name>` to validate that the story reached at least that named phase. Resume always continues from the latest `pipeline_state.json` snapshot regardless of the named savepoint provided.

The `tui` subcommand lazily imports `StoryWriterApp`. If `textual` is missing, the CLI exits with an install hint instead of breaking `run` or `resume`.

### Layout

The app uses a three-panel layout defined in `src/presentation/tui/app.tcss`:

| Panel | Location | Purpose |
|------|----------|---------|
| Phase tracker | Left | Shows the simplified pipeline stages used by the TUI: `outline`, `chapters`, `wiki`, `final-edit`, `assembly` |
| Output log | Centre | Streams model tokens and status messages into a `RichLog` |
| Wiki context | Right | Shows wiki-context events emitted during retrieval and maintenance work |

The wiki panel starts hidden. The approval input widget also starts hidden and appears only while the pipeline is waiting on a human decision.

### Keybindings And Input

| Input | Effect |
|------|--------|
| `Ctrl+W` | Toggle the wiki context panel |
| `Ctrl+C` | Cancel workers, preserve the savepoint from the last completed phase, and print the resume command |
| `approve` | Approve the current gate and continue |
| `reject` | Reject the current gate |
| `revise <feedback>` | Request a revision and pass free-text feedback back into the pipeline |

Free text that does not match `approve`, `reject`, or `revise <feedback>` is treated as revision feedback.

Manual savepoint hotkeys are no longer exposed in the TUI. Savepoints are written automatically at pipeline phase boundaries.

## Developer Guide

### Key Files

- `src/presentation/tui/app.py` — `StoryWriterApp`, `TUIApprovalGate`, worker-thread bridge logic, and widget event handlers
- `src/presentation/tui/app.tcss` — layout and panel styling
- `src/presentation/cli/main.py` — `story-writer tui` command dispatch
- `src/presentation/pipeline_primitives.py` — transport primitives consumed by the TUI
- `tests/unit/test_tui.py` — Textual Pilot coverage for layout, keybindings, and approval-gate flow

### Thread Model

The TUI keeps the Textual event loop responsive by running the pipeline in a worker thread:

1. `StoryWriterApp.on_mount()` calls `_run_pipeline()`.
2. `_run_pipeline()` is decorated with `@work(thread=True)`, so Textual executes it off the UI thread.
3. The worker thread calls `asyncio.run(_run())`.
4. `_run()` creates the token bus and wiki bus, then `await asyncio.gather(...)` runs three coroutines together:
   - `run_pipeline(story_name, gate, bus, wiki_bus)` for fresh runs, or `resume_pipeline(story_name, savepoint_name, gate, bus, wiki_bus)` for resumed runs
   - `_drain_tokens(bus)`
   - `_drain_wiki(wiki_bus)`
5. A `finally` block closes both buses so the drain coroutines terminate cleanly even on failure.

This design keeps a single source of truth for orchestration while still allowing live UI updates.

### Approval Gate Bridging

`TUIApprovalGate` extends `ApprovalGate` to bridge the worker-thread event loop and the Textual UI loop safely:

- `await_decision()` runs inside the worker thread, captures the worker event loop, creates the pending future, and uses `call_from_thread()` to reveal the footer input widget.
- `on_input_submitted()` parses the user's text into an `ApprovalDecision`.
- `resolve_from_ui()` uses `loop.call_soon_threadsafe()` to resolve the worker-thread future from the UI thread.
- If the UI submits a decision before the worker starts awaiting, the decision is cached in `_pending_decision` and returned on the next `await_decision()` call.

The bridge avoids direct cross-thread widget access and keeps the orchestrator transport-agnostic.

### Bus Drain Pattern

The TUI does not let producer code touch widgets directly. Instead, it drains both async buses and forwards each event into the UI thread:

- `_drain_tokens()` iterates over `TokenStreamBus` and forwards each token delta to `_append_token()` with `call_from_thread()`.
- `_drain_wiki()` iterates over `WikiContextBus` and forwards each `WikiContextEvent` to `_append_wiki_event()` the same way.
- `_append_wiki_event()` also normalises internal phase names such as `chapter-loop`, `chapter-1`, `characters`, and `settings` into the simplified TUI phase list.

Because both buses are queue-backed async iterators, the worker can stream output incrementally while the UI stays isolated from thread-bound asyncio state.

## Testing

Issue #163 adds 11 unit tests in `tests/unit/test_tui.py`.

Coverage focuses on the TUI presentation contract rather than the full live pipeline:

- app composition without launching the real worker
- hidden-on-mount behaviour for the wiki panel and approval input
- `Ctrl+W` wiki-panel toggling through Textual Pilot
- parsing of `approve`, `reject`, `revise <feedback>`, and free-text revision input
- approval submission resolving the pending gate future
- `Ctrl+C` logging the preserved savepoint message for cooperative cancellation
- resume mode dispatching `resume_pipeline()` instead of `run_pipeline()`
- `TUIApprovalGate.resolve_from_ui()` using `call_soon_threadsafe()`

Run the focused test file with:

```bash
pytest tests/unit/test_tui.py -q
```

## Related

- [Pipeline Primitives](./pipeline-primitives.md)
- [Story Orchestrator](./story-orchestrator.md)
- [Tools Reference](../tools.md)
- [Comprehensive Manual](../manual.md)
- [PRD: Python-Native Orchestration and TUI](../planning/python-native-migration/prd.md)