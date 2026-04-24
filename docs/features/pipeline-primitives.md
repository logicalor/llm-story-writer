# Pipeline Primitives

> Transport-agnostic async approval and event-stream primitives introduced for Issue #160 and PR #170.

## Overview

Issue #160 adds `src/presentation/pipeline_primitives.py`, a small presentation-layer module that gives the Python-native orchestrator three shared coordination primitives: approval gates, token streaming, and wiki context event streaming. The module keeps the orchestrator independent from any specific transport or UI. It exposes plain asyncio-based objects that a Textual TUI, a headless runner, or later presentation layers can all use without changing orchestration code.

This work is the first presentation-layer slice of the Python-native migration after the earlier typed handoff foundation from Issue #158. The `ApprovalDecision` dataclass defined there remains the gate result type here, while the new module adds the async control surfaces that Task 5's orchestrator will consume.

## User Guide

### Approval Gates

`ApprovalGate` is an `asyncio.Future`-backed pause point. The orchestrator creates a gate before a human approval boundary, awaits `await_decision()`, and resumes only when some consumer resolves the gate.

```python
import asyncio

from application.pipeline.handoffs import ApprovalDecision
from presentation.pipeline_primitives import ApprovalGate


async def main() -> None:
    gate = ApprovalGate()

    async def resolve_later() -> None:
        await asyncio.sleep(0.1)
        gate.resolve(ApprovalDecision(approved=True))

    asyncio.create_task(resolve_later())
    decision = await gate.await_decision()
    print(decision.approved)


asyncio.run(main())
```

In interactive mode, a TUI owns the `resolve()` call after the user approves, rejects, or requests revision. In batch or headless mode, use `NullApprovalGate` instead. Its `await_decision()` method returns `ApprovalDecision(approved=True, auto_approved=True)` immediately, so unattended runs never block on human input.

### Token Streaming

`TokenStreamBus` is an `asyncio.Queue`-backed async iterator for streamed token deltas. Producers call `emit(delta)` for each chunk and `close()` when generation finishes. Consumers use `async for` to receive the stream in emission order.

```python
import asyncio

from presentation.pipeline_primitives import TokenStreamBus


async def producer(bus: TokenStreamBus) -> None:
    await bus.emit("Once ")
    await bus.emit("upon ")
    await bus.emit("a time")
    bus.close()


async def consumer(bus: TokenStreamBus) -> str:
    chunks = [chunk async for chunk in bus]
    return "".join(chunks)


async def main() -> None:
    bus = TokenStreamBus()
    _, text = await asyncio.gather(producer(bus), consumer(bus))
    print(text)


asyncio.run(main())
```

The primitive does not know whether the consumer is a TUI log, a test harness, or no consumer at all. That separation is the point: producers emit deltas once, while presentation code decides whether to render them, discard them, or aggregate them.

### Wiki Context Events

`WikiContextEvent` is a dataclass describing one step in wiki context assembly:

| Field | Meaning |
|-------|---------|
| `phase` | Pipeline phase emitting the event |
| `event_type` | Event category such as `entity_match`, `wikilink_traversal`, or `detail_level` |
| `content` | Human-readable event text |
| `metadata` | Extra structured details for the consumer |

`WikiContextBus` mirrors `TokenStreamBus`, but yields `WikiContextEvent` objects instead of strings.

```python
import asyncio

from presentation.pipeline_primitives import WikiContextBus, WikiContextEvent


async def producer(bus: WikiContextBus) -> None:
    await bus.emit(
        WikiContextEvent(
            phase="outline",
            event_type="entity_match",
            content="Matched captain-vela",
            metadata={"score": 0.92},
        )
    )
    bus.close()


async def main() -> None:
    bus = WikiContextBus()
    asyncio.create_task(producer(bus))

    async for event in bus:
        print(event.phase, event.event_type, event.content)


asyncio.run(main())
```

In the planned TUI, this bus feeds the wiki context panel. In headless mode, the orchestrator can still emit the same events while the runner ignores them or drains them with a no-op consumer.

## Developer Guide

### Key Files

- `src/presentation/pipeline_primitives.py` — approval gates, token bus, wiki context event dataclass, wiki context bus
- `src/application/pipeline/handoffs.py` — `ApprovalDecision` type consumed by approval gates
- `tests/unit/test_pipeline_primitives.py` — unit coverage for blocking, ordering, and stream closure

### Design Notes

- `ApprovalGate` creates its `asyncio.Future` inside `await_decision()`, so gate resolution always binds to the running event loop that awaits it.
- `NullApprovalGate` subclasses `ApprovalGate` but overrides `await_decision()` to return immediately. It exists specifically for batch and headless execution paths.
- Both buses use one module-level `_SENTINEL = object()` to mark end-of-stream. `close()` enqueues that sentinel, and async iteration exits when it is received.
- Items emitted before `close()` remain readable after closure because the sentinel is queued after existing items.
- The buses preserve emission order because `asyncio.Queue` is FIFO and the iterators yield items exactly as dequeued.

### Consumer Patterns

| Primitive | Producer role | Interactive consumer | Batch/headless behaviour |
|-----------|---------------|----------------------|--------------------------|
| `ApprovalGate` | Orchestrator pauses at approval boundary | TUI resolves gate from user input | Replace with `NullApprovalGate` to auto-approve |
| `TokenStreamBus` | LLM-facing phase emits token deltas | TUI drains chunks into streaming output panel | Runner may skip consumption or drain without rendering |
| `WikiContextBus` | Wiki retrieval phase emits structured context events | TUI shows entity matches, traversal, and detail-level choices | Runner may ignore or no-op consume events |

### Testing

Issue #160 adds six unit tests in `tests/unit/test_pipeline_primitives.py`:

- `test_approval_gate_block_resolve` verifies the gate blocks until `resolve()` sets a decision
- `test_null_approval_gate_returns_approve_immediately` verifies headless auto-approval
- `test_token_stream_bus_ordering` verifies token chunk ordering
- `test_wiki_context_bus_ordering` verifies wiki event ordering
- `test_close_before_consume` verifies pre-close items still arrive when consumption starts later
- `test_close_mid_consume` verifies iteration terminates cleanly after closure during active consumption

Run the focused test file with:

```bash
pytest tests/unit/test_pipeline_primitives.py -q
```

## Related

- [Python-Native Foundation](./python-native-foundation.md)
- [OpenAI Async Provider](./openai-async-provider.md)
- [PRD: Python-Native Orchestration and TUI](../planning/python-native-migration/prd.md)
- Issue #160 — Python-native migration [3/9]: Pipeline primitives
- PR #170 — Python-native migration [3/9]: Pipeline primitives
