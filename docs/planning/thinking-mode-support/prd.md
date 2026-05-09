# PRD: Thinking Mode Support (Gemma 4 / LM Studio)

> Expose the model's reasoning channel (`reasoning_content`) through the streaming pipeline and render it distinctly in the TUI, so operators can observe model thinking separately from generated content.

**Date:** 2026-05-10
**Author:** Planner agent
**Status:** Draft

---

## Problem Statement

Gemma 4 (and compatible reasoning-capable models) expose a separate reasoning channel alongside their final content. When LM Studio is configured with Reasoning Parsing enabled, the OpenAI-compatible API returns this channel as a distinct field — `reasoning_content` — on the response `message` object, and as a similarly distinct delta field during streaming.

The pipeline currently ignores `reasoning_content` entirely. The provider's `stream_text` method only yields `delta.content` tokens, so thinking output is silently dropped. The provider's non-streaming path calls `_filter_think_tags` to strip residual `<think>…</think>` markup, which can also silently discard genuine reasoning text that leaks into the content field when LM Studio's tag parsing does not cleanly separate the two channels.

The result is that users cannot observe model reasoning at all — neither during generation nor in debug logs — even though the model is producing it and it contains information useful for diagnosing generation quality and understanding model behaviour.

---

## Goals

1. The streaming infrastructure must propagate both thinking tokens and content tokens from the provider to upstream consumers, with each token tagged to indicate its channel.
2. The TUI must display thinking tokens in a visually distinct manner, making the two channels immediately distinguishable at a glance.
3. The content stream consumed by the pipeline (for prose accumulation, quality review, etc.) must remain exclusively final-content tokens; thinking tokens must never contaminate persisted prose.
4. The feature must be backward-compatible: models that do not emit `reasoning_content` continue to work without any configuration change.

---

## Non-Goals

- Persisting or logging thinking content to disk (savepoints, story state, debug log). Thinking is transient observational output — it is not an input to downstream pipeline stages.
- Modifying any prompt template or injecting `<|think|>` tokens. The user has already configured LM Studio's prompt template and Reasoning Parsing. This feature only handles what the API returns.
- Supporting thinking for the synchronous `_llm.py` tool path. That path is used by non-streaming tool scripts (wiki, recap, etc.) that do not have access to a bus. Thinking output from those calls is irrelevant to the user.
- Supporting other inference providers (e.g., `openai_compatible_provider.py`, `prompt_handler.py`). Gemma 4 / LM Studio routes exclusively through `OpenAIAsyncProvider`.

---

## User Stories

### Pipeline Operator

- As a pipeline operator, I want to watch the model's reasoning stream in real time during chapter generation, so that I can assess whether the model is reasoning coherently before the final prose appears.
- As a pipeline operator, I want the TUI to visually separate thinking tokens from content tokens, so that I can distinguish model reasoning from story output at a glance.
- As a pipeline operator, I want thinking tokens to appear in the Activity panel (not the main output log), so that the content log remains a clean transcript of generated prose.

### Developer

- As a developer, I want the `stream_text` generator to yield typed `StreamToken` objects rather than raw strings, so that consumers can branch on token kind without string-parsing heuristics.
- As a developer, I want the change to be backward-compatible, so that agents that do not need to distinguish token kinds can call a helper that extracts content text from the tagged stream without modification.

---

## Proposed Solution

### Core design: `StreamToken` tagged union

Replace the `str` yield type of `stream_text` with a lightweight `StreamToken` dataclass:

```python
@dataclass
class StreamToken:
    text: str
    kind: Literal["content", "thinking"]  # "thinking" = reasoning_content
```

`OpenAIAsyncProvider.stream_text` inspects `delta.content` and, when available, `delta.model_extra.get("reasoning_content")` on each streaming chunk, yielding typed `StreamToken` objects.

The non-streaming path (`generate_text`) reads `message.reasoning_content` from the completed response and passes it through to the debug log (discarded from the return value, which stays content-only).

### Pipeline layer: `_stream_to_bus` update

`ChapterWriterAgent._stream_to_bus` (and equivalent helpers in other agents that call `stream_text`) is updated to:

1. Accumulate only `kind == "content"` tokens into `full_text` (the return value that feeds prose persistence).
2. Emit content tokens to `self.bus` as today.
3. Emit thinking tokens to `self.bus` with a sentinel prefix (e.g. `\x00think\x00`) **or** via a new dedicated `ThinkingStreamBus`.

The preferred approach is a **dedicated `ThinkingStreamBus`** (same structure as `TokenStreamBus`) rather than a sentinel-prefixed single bus. This keeps the two channels cleanly separated without requiring consumers to parse escape sequences, and avoids ambiguity if thinking content itself contains the sentinel string.

### TUI layer: thinking panel

The TUI drains `ThinkingStreamBus` in a dedicated `_drain_thinking` coroutine. Thinking tokens are routed to the **Activity panel** (the right-hand `#wiki-log` `RichLog`), prefixed with a `[think]` tag and the current timestamp, using a visually distinct format:

```
14:32:07 💭 [think] The protagonist's arc in this chapter should...
```

This reuses the existing Activity panel infrastructure rather than adding a third column, keeping the layout unchanged.

### Provider layer: `reasoning_content` extraction

The OpenAI Python SDK exposes non-standard fields via `model_extra` on the response object. For streaming chunks, `chunk.choices[0].delta.model_extra.get("reasoning_content")` is checked. For non-streaming responses, `response.choices[0].message.model_extra.get("reasoning_content")` is checked. Both are guarded with `or ""` defaults so non-thinking models produce no change in behaviour.

### ModelProvider interface

The `stream_text` abstract method signature changes from `AsyncGenerator[str, None]` to `AsyncGenerator[StreamToken, None]`. All existing call sites in the six agents (`chapter_writer`, `outline_planner`, `story_planner`, `consistency_checker`, `chapter_outline_expander`, `quality_reviewer`, `final_editor`) and in `prompt_handler` are updated to consume `StreamToken` objects. Each site gets a one-line helper or inline filter to extract `.text` when only content is needed.

---

## Acceptance Criteria

- [ ] `StreamToken` dataclass defined in `presentation/pipeline_primitives.py` with `text: str` and `kind: Literal["content", "thinking"]`.
- [ ] `ThinkingStreamBus` class added to `presentation/pipeline_primitives.py`, structurally identical to `TokenStreamBus`.
- [ ] `OpenAIAsyncProvider.stream_text` yields `StreamToken` objects; `reasoning_content` deltas yield `kind="thinking"`, content deltas yield `kind="content"`.
- [ ] `OpenAIAsyncProvider.generate_text` (non-streaming path) reads `reasoning_content` from the completed response and appends it to the debug log under a `"reasoning"` key; the method return value is content-only.
- [ ] `ChapterWriterAgent._stream_to_bus` accumulates only `kind="content"` tokens into the returned prose string; `kind="thinking"` tokens are emitted to a `ThinkingStreamBus`.
- [ ] All other agents that call `stream_text` filter to content tokens only (thinking tokens are discarded at the call site if those agents have no thinking bus).
- [ ] `ModelProvider.stream_text` abstract signature updated to `AsyncGenerator[StreamToken, None]`.
- [ ] `StoryWriterApp` drains `ThinkingStreamBus` in a `_drain_thinking` coroutine; thinking tokens appear in the `#wiki-log` Activity panel with a `💭 [think]` prefix.
- [ ] Non-thinking models (no `reasoning_content` in response) produce no behavioural change.
- [ ] `_filter_think_tags` in `OpenAIAsyncProvider` is removed (now redundant; thinking is separated at the API response level).
- [ ] Unit tests: `StreamToken` construction and field access; `ThinkingStreamBus` emit/drain; `stream_text` yields correct `StreamToken.kind` for both content and reasoning deltas (using a mocked OpenAI stream); `_stream_to_bus` accumulates only content tokens; TUI `_drain_thinking` routes thinking tokens to wiki-log.

---

## Open Questions

- None. The user has confirmed LM Studio is configured and working; the feature scope is fully bounded.

---

## Related

- [LM Studio / Gemma 4 thinking mode guide](https://antonioleiva.com/enable-gemma-thinking-mode-lm-studio-opencode)
- `src/infrastructure/providers/openai_async_provider.py` — primary change site
- `src/presentation/pipeline_primitives.py` — new types
- `src/presentation/agents/chapter_writer.py` — `_stream_to_bus` update
- `src/presentation/tui/app.py` — `_drain_thinking` and Activity panel routing
