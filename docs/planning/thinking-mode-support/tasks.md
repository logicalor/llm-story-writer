# Task Breakdown: Thinking Mode Support

> Implements [PRD](./prd.md)

**Date:** 2026-05-10

---

## Tasks

### Task 1: Add `StreamToken` and `ThinkingStreamBus` to pipeline primitives

**Type:** backend
**Estimated scope:** small
**Dependencies:** none

**Description:**

Add two new types to `src/presentation/pipeline_primitives.py`:

1. `StreamToken` — a dataclass with `text: str` and `kind: Literal["content", "thinking"]`. This is the tagged union that replaces the bare `str` yielded by `stream_text`.
2. `ThinkingStreamBus` — structurally identical to `TokenStreamBus` but typed to carry `StreamToken` objects. Its queue type is `asyncio.Queue[StreamToken | object]`. It follows the same sentinel/close/`__aiter__` pattern as `TokenStreamBus`.

No changes to existing types in this file. No changes to any consumer yet.

**Acceptance Criteria:**

- [ ] `StreamToken(text="hello", kind="content")` and `StreamToken(text="...", kind="thinking")` construct without error.
- [ ] `ThinkingStreamBus.emit(token)` and async-iteration over `ThinkingStreamBus` round-trip a `StreamToken` correctly.
- [ ] `pipeline_primitives` module exports `StreamToken` and `ThinkingStreamBus`.
- [ ] Unit tests in `tests/unit/test_pipeline_primitives.py` cover both new types.

**Key Files:**

- `src/presentation/pipeline_primitives.py` — add `StreamToken` dataclass and `ThinkingStreamBus` class

---

### Task 2: Update `ModelProvider` interface and `OpenAIAsyncProvider.stream_text`

**Type:** backend
**Estimated scope:** medium
**Dependencies:** Task 1

**Description:**

Two changes in `src/infrastructure/providers/openai_async_provider.py`:

**`stream_text`:** Change the generator to yield `StreamToken` instead of `str`. For each SSE chunk from the OpenAI SDK:
- If `delta.content` is non-empty → yield `StreamToken(text=delta.content, kind="content")`.
- If `delta.model_extra` contains a non-empty `"reasoning_content"` value → yield `StreamToken(text=delta.model_extra["reasoning_content"], kind="thinking")`.
- A chunk may carry both fields simultaneously; yield both tokens in order (`thinking` first, then `content`), matching LM Studio's emission order.

Guard `model_extra` access with `getattr(delta, "model_extra", None) or {}` to handle SDK versions that do not expose the attribute.

**`generate_text` (non-streaming path):** After receiving the completed response, check `response.choices[0].message.model_extra.get("reasoning_content", "")`. Append it to the debug log under a `"reasoning"` key. The method return value is unchanged (content-only).

**`generate_text` (streaming path):** The internal loop that calls `self.stream_text` must filter for `kind == "content"` tokens when building the `chunks` list passed to `_filter_think_tags`. Since thinking is now cleanly separated at the API level, `_filter_think_tags` is no longer needed — remove its call from the streaming path and remove the method itself.

Update `src/application/interfaces/model_provider.py`: change the `stream_text` abstract return type from `AsyncGenerator[str, None]` to `AsyncGenerator[StreamToken, None]`. Import `StreamToken` from `presentation.pipeline_primitives`.

**Acceptance Criteria:**

- [ ] `stream_text` return annotation is `AsyncGenerator[StreamToken, None]` in both the abstract base and the concrete implementation.
- [ ] A mocked OpenAI streaming response with both `content` and `reasoning_content` deltas produces `StreamToken` objects with the correct `kind` values.
- [ ] A mocked response with only `content` deltas produces only `kind="content"` tokens (no `kind="thinking"` tokens emitted).
- [ ] `_filter_think_tags` is deleted from `OpenAIAsyncProvider`.
- [ ] Non-streaming `generate_text` still returns a plain `str` (content only); reasoning content appears in debug log if `LLM_DEBUG_LOG` is set.
- [ ] `ModelProvider` abstract base compiles with the updated `stream_text` signature.
- [ ] Unit tests in `tests/unit/test_openai_async_provider.py` cover both thinking and non-thinking chunk scenarios.

**Key Files:**

- `src/infrastructure/providers/openai_async_provider.py` — `stream_text`, `generate_text` (streaming path), delete `_filter_think_tags`
- `src/application/interfaces/model_provider.py` — update `stream_text` return type annotation

---

### Task 3: Update `ChapterWriterAgent._stream_to_bus` to route thinking tokens

**Type:** backend
**Estimated scope:** small
**Dependencies:** Task 1, Task 2

**Description:**

`ChapterWriterAgent` is the primary streaming consumer. `_stream_to_bus` currently accumulates every `str` token into `full_text` and emits it to `self.bus`. After this task:

- `_stream_to_bus` receives a `ThinkingStreamBus | None` parameter (default `None`, for call sites that don't have one yet).
- It iterates over `StreamToken` objects from `stream_text`.
- `kind == "content"` tokens: accumulated into `full_text`; emitted to `self.bus`.
- `kind == "thinking"` tokens: emitted to the `ThinkingStreamBus` if one is provided; otherwise silently discarded.
- `ChapterWriterAgent.__init__` gains an optional `thinking_bus: ThinkingStreamBus | None = None` parameter, stored as `self.thinking_bus`.
- All `_stream_to_bus(messages, config, seed)` call sites within `chapter_writer.py` pass `self.thinking_bus` as the new parameter.

All other agents that call `provider.stream_text` directly (not via `_stream_to_bus`) are updated inline to filter to `kind == "content"` tokens only. They have no thinking bus and discard thinking tokens silently. Affected agents:
- `consistency_checker.py`
- `chapter_outline_expander.py`
- `outline_planner.py`
- `story_planner.py`
- `quality_reviewer.py`
- `final_editor.py`
- `prompt_handler.py` (infrastructure)

The fix in each is a one-line filter: replace `async for token in self.provider.stream_text(...)` with `async for st in self.provider.stream_text(...):` and use `st.text` where `token` was used, only when `st.kind == "content"`.

**Acceptance Criteria:**

- [ ] `_stream_to_bus` return value contains only content text (verified by unit test with mixed `StreamToken` sequence).
- [ ] `kind="thinking"` tokens from `_stream_to_bus` are forwarded to the `ThinkingStreamBus` when provided.
- [ ] All other agent call sites compile without error with the new `StreamToken` yield type.
- [ ] No prose content is lost (content tokens still flow to `self.bus` and accumulate in return value).
- [ ] `ChapterWriterAgent` can be constructed without a `thinking_bus` (backward-compatible default).
- [ ] Unit tests: mock `stream_text` with mixed content/thinking tokens; assert `_stream_to_bus` return value is content-only; assert thinking bus received thinking tokens.

**Key Files:**

- `src/presentation/agents/chapter_writer.py` — `__init__`, `_stream_to_bus`, all call sites
- `src/presentation/agents/consistency_checker.py` — inline filter
- `src/presentation/agents/chapter_outline_expander.py` — inline filter
- `src/presentation/agents/outline_planner.py` — inline filter
- `src/presentation/agents/story_planner.py` — inline filter
- `src/presentation/agents/quality_reviewer.py` — inline filter
- `src/presentation/agents/final_editor.py` — inline filter
- `src/infrastructure/prompts/prompt_handler.py` — inline filter

---

### Task 4: Wire `ThinkingStreamBus` through the orchestrator and TUI

**Type:** full-stack
**Estimated scope:** medium
**Dependencies:** Task 1, Task 3

**Description:**

**Orchestrator (`src/presentation/orchestrator.py`):**

`run_pipeline` and `resume_pipeline` already accept `bus` and `wiki_bus`. Add a `thinking_bus: ThinkingStreamBus | None = None` parameter to both. Where `ChapterWriterAgent` is constructed, pass `thinking_bus=thinking_bus` (or `thinking_bus=None` if the caller did not provide one). No other orchestrator changes needed.

**TUI (`src/presentation/tui/app.py`):**

1. In `_run_pipeline`, construct a `ThinkingStreamBus()` alongside the existing `TokenStreamBus()`.
2. Add a `_drain_thinking` coroutine that iterates the `ThinkingStreamBus` and calls `self.call_from_thread(self._append_thinking_token, st)` for each `StreamToken`.
3. Add `_append_thinking_token(self, st: StreamToken)` method. It writes to the `#wiki-log` `RichLog` with a `💭 [think]` prefix and current timestamp:
   ```
   14:32:07 💭 [think] <thinking token text>
   ```
   Because thinking output is streamed token-by-token, accumulate tokens into a `_thinking_buffer: list[str]` (analogous to `_token_buffer`) and flush on newline or buffer size threshold.
4. Include `_drain_thinking(thinking_bus)` in the `asyncio.gather()` call alongside the existing drain coroutines. Pass `thinking_bus=thinking_bus` to `run_pipeline` / `resume_pipeline`.
5. Call `thinking_bus.close()` in the `finally` block of `_pipeline_with_close`.

**Headless / batch mode:** `NullApprovalGate` path creates a `ThinkingStreamBus` but nothing drains it. This is safe because the bus queue grows without bound only if the producer runs without the consumer, which cannot happen in practice (the pipeline worker and the `asyncio.gather` run together).

**Acceptance Criteria:**

- [ ] `run_pipeline` and `resume_pipeline` signatures include `thinking_bus: ThinkingStreamBus | None = None`.
- [ ] `ChapterWriterAgent` is constructed with the `thinking_bus` from the orchestrator call site.
- [ ] `StoryWriterApp._run_pipeline` creates a `ThinkingStreamBus`, passes it to the pipeline, and drains it in `_drain_thinking`.
- [ ] Thinking tokens appear in `#wiki-log` with `💭 [think]` prefix and timestamp.
- [ ] `thinking_bus.close()` is called in the pipeline `finally` block.
- [ ] Integration test or unit test: construct a `ThinkingStreamBus`, emit a `StreamToken(kind="thinking")`, verify TUI `_append_thinking_token` writes to the activity panel.

**Key Files:**

- `src/presentation/orchestrator.py` — `run_pipeline`, `resume_pipeline`, `ChapterWriterAgent` construction site
- `src/presentation/tui/app.py` — `_run_pipeline`, `_drain_thinking`, `_append_thinking_token`, `_thinking_buffer`

---

### Task 5: Update debug log to capture reasoning content

**Type:** backend
**Estimated scope:** small
**Dependencies:** Task 2

**Description:**

Update `_append_debug_log` in `openai_async_provider.py` to accept an optional `reasoning: str` parameter. When provided and non-empty, include it in the JSONL record under the key `"reasoning"`. Update the call site in `generate_text` (non-streaming path) to pass the extracted `reasoning_content`.

For the streaming path, accumulate `kind="thinking"` tokens into a `thinking_chunks: list[str]` alongside `chunks` (content). Pass the joined thinking text to `_append_debug_log` as `reasoning`.

This task is optional for TUI observability but completes the audit trail.

**Acceptance Criteria:**

- [ ] JSONL debug log records include a `"reasoning"` field when `reasoning_content` is non-empty.
- [ ] Records from non-thinking models have no `"reasoning"` key (absent, not `null`).
- [ ] Unit test: `_append_debug_log` with and without `reasoning` argument produces correct JSONL.

**Key Files:**

- `src/infrastructure/providers/openai_async_provider.py` — `_append_debug_log`, `generate_text` (both paths)

---

### Task 6: Tests and lint/type check

**Type:** backend
**Estimated scope:** medium
**Dependencies:** Tasks 1–5

**Description:**

Write or update tests to cover all new behaviour. Ensure `ruff`, `mypy`, and `pytest` all pass cleanly.

**Test files to create or update:**

- `tests/unit/test_pipeline_primitives.py` — `StreamToken` construction, field access; `ThinkingStreamBus` emit/drain round-trip.
- `tests/unit/test_openai_async_provider.py` — `stream_text` with mocked OpenAI SDK chunks:
  - chunk with only `content` → `kind="content"` token
  - chunk with only `reasoning_content` → `kind="thinking"` token
  - chunk with both → two tokens, thinking first
  - chunk with neither → no token emitted
  - non-streaming `generate_text` extracts `reasoning_content` into debug log, returns content-only string
- `tests/unit/test_chapter_writer.py` (existing) — update stubs where `stream_text` now yields `StreamToken`; add test for `_stream_to_bus` content/thinking separation.
- `tests/unit/test_tui.py` (existing) — add test for `_append_thinking_token` routing to `#wiki-log`.

All existing tests must pass without modification (backward-compat) except where stubs need to yield `StreamToken` instead of `str`.

**Acceptance Criteria:**

- [ ] `pytest tests/unit/ -v` passes with 0 failures.
- [ ] `ruff check --fix . && ruff format .` reports no issues.
- [ ] `mypy src/` reports no new errors.

**Key Files:**

- `tests/unit/test_pipeline_primitives.py` — new or updated
- `tests/unit/test_openai_async_provider.py` — new or updated
- `tests/unit/test_chapter_writer.py` — stub updates
- `tests/unit/test_tui.py` — new `_append_thinking_token` test
