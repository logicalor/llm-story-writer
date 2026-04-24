"""Transport-agnostic async pipeline primitives.

ApprovalGate, TokenStreamBus, and WikiContextBus decouple the pipeline
orchestrator from its consumer (TUI or headless runner). All three
primitives are created by the orchestrator and passed to the consumer
before the pipeline starts.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from application.pipeline.handoffs import ApprovalDecision


class ApprovalGate:
    """Async approval gate backed by asyncio.Future.

    The orchestrator awaits .await_decision() at phase boundaries.
    The TUI calls .resolve() when the user submits input.
    """

    def __init__(self) -> None:
        self._future: asyncio.Future[ApprovalDecision] | None = None

    async def await_decision(self) -> ApprovalDecision:
        """Block until .resolve() is called and return the decision."""
        loop = asyncio.get_running_loop()
        self._future = loop.create_future()
        return await self._future

    def resolve(self, decision: ApprovalDecision) -> None:
        """Resolve the pending gate with the given decision."""
        if self._future is not None and not self._future.done():
            self._future.set_result(decision)


class NullApprovalGate(ApprovalGate):
    """Auto-approving gate for batch/headless mode.

    Returns ApprovalDecision(approved=True, auto_approved=True) immediately
    without blocking.
    """

    async def await_decision(self) -> ApprovalDecision:
        """Return APPROVE immediately without blocking."""
        return ApprovalDecision(approved=True, auto_approved=True)


_SENTINEL = object()  # signals end-of-stream for bus iterators


class TokenStreamBus:
    """Async token stream backed by asyncio.Queue.

    Producer: .emit(delta) for each token, .close() when done.
    Consumer: async iteration yields token strings.
    """

    def __init__(self) -> None:
        self._queue: asyncio.Queue[str | object] = asyncio.Queue()
        self._closed = False

    async def emit(self, delta: str) -> None:
        """Emit a token delta to the stream."""
        await self._queue.put(delta)

    def close(self) -> None:
        """Signal end-of-stream to consumers."""
        self._closed = True
        self._queue.put_nowait(_SENTINEL)

    def __aiter__(self) -> AsyncIterator[str]:
        return self._iterate()

    async def _iterate(self) -> AsyncIterator[str]:
        while True:
            item = await self._queue.get()
            if item is _SENTINEL:
                break
            yield item  # type: ignore[misc]


@dataclass
class WikiContextEvent:
    """A structured event emitted during wiki context assembly.

    Produced by: context retrieval pipeline (entity matching, wikilink
    traversal, detail-level selection).
    Consumed by: TUI wiki context panel or headless no-op consumer.
    """

    phase: str
    event_type: str  # "entity_match" | "wikilink_traversal" | "detail_level"
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


class WikiContextBus:
    """Async wiki context event bus backed by asyncio.Queue.

    Producer: .emit(event) for each context event, .close() when done.
    Consumer: async iteration yields WikiContextEvent objects.
    """

    def __init__(self) -> None:
        self._queue: asyncio.Queue[WikiContextEvent | object] = asyncio.Queue()
        self._closed = False

    async def emit(self, event: WikiContextEvent) -> None:
        """Emit a wiki context event."""
        await self._queue.put(event)

    def close(self) -> None:
        """Signal end-of-stream to consumers."""
        self._closed = True
        self._queue.put_nowait(_SENTINEL)

    def __aiter__(self) -> AsyncIterator[WikiContextEvent]:
        return self._iterate()

    async def _iterate(self) -> AsyncIterator[WikiContextEvent]:
        while True:
            item = await self._queue.get()
            if item is _SENTINEL:
                break
            yield item  # type: ignore[misc]
