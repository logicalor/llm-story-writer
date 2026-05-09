# ADR 016: `StreamToken` Tagged Union for Thinking-Capable Model Output

**Date:** 2026-05-10
**Status:** Proposed

---

## Context

Gemma 4 and other reasoning-capable models expose a dedicated reasoning channel (`reasoning_content`) alongside the final content channel when served through LM Studio's OpenAI-compatible API. The current `ModelProvider.stream_text` interface yields bare `str` tokens with no channel information. This means:

1. Thinking output is either silently dropped (streaming path ignores `reasoning_content` deltas) or defensively stripped via `_filter_think_tags` (non-streaming path removes `<think>…</think>` markup that leaks into the content field when tag parsing is imperfect).
2. No consumer can distinguish a thinking token from a content token without fragile string-parsing heuristics.
3. The TUI cannot display thinking output because there is no channel to carry it.

A decision is needed on how to represent two distinct token channels through a single async generator interface without breaking existing consumers.

---

## Decision

Introduce a `StreamToken` dataclass as the yield type of `ModelProvider.stream_text`:

```python
@dataclass
class StreamToken:
    text: str
    kind: Literal["content", "thinking"]
```

`stream_text` is updated from `AsyncGenerator[str, None]` to `AsyncGenerator[StreamToken, None]` everywhere: the abstract base, `OpenAIAsyncProvider`, and `openai_compatible_provider` (pass-through — it never generates thinking tokens, so it always yields `kind="content"`).

A `ThinkingStreamBus` (queue-backed async bus, structurally identical to `TokenStreamBus`) carries `StreamToken` objects from the provider through `ChapterWriterAgent._stream_to_bus` to the TUI, where they are rendered in the Activity panel with a `💭 [think]` prefix.

Agents that do not need to observe thinking (all agents except `ChapterWriterAgent`) filter to `kind == "content"` tokens inline at their `stream_text` call site; they have no `ThinkingStreamBus` reference.

---

## Consequences

### Positive

- Clean separation of channels at the API boundary; no string-parsing heuristics required anywhere downstream.
- The `_filter_think_tags` method in `OpenAIAsyncProvider` becomes redundant and is deleted, removing a fragile regex that could incorrectly strip model-generated content that happens to contain `<think>` as story text.
- The `ThinkingStreamBus` is optional at every layer — callers that pass `None` (or omit it) continue to work as before; thinking tokens are silently discarded.
- The debug log can record reasoning content without changing the on-disk content format (it is an additive field in the JSONL record).
- The TUI Activity panel is reused rather than adding a third panel column, keeping the layout stable.

### Negative

- All six agent files that call `stream_text` require a one-line update to handle `StreamToken` instead of `str`. This is mechanical but touches many files.
- Existing tests that stub `stream_text` to yield `str` values must be updated to yield `StreamToken` objects. The update is mechanical but broad.
- `ModelProvider` is an abstract base; any third-party or future provider must implement the new signature. The `openai_compatible_provider` is updated as a pass-through (always `kind="content"`), establishing the precedent.

### Neutral

- The `ThinkingStreamBus` adds one more bus to the `asyncio.gather` call in `StoryWriterApp._run_pipeline`. This is structurally identical to the existing `WikiContextBus` drain — no new patterns are introduced.
- Thinking tokens are not persisted to savepoints, story state, or chapter prose. This is intentional: thinking is transient observational output and must not contaminate the content pipeline.
