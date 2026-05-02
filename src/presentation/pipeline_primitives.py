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
        self._pending_decision: ApprovalDecision | None = None

    async def await_decision(self) -> ApprovalDecision:
        """Block until .resolve() is called and return the decision."""
        if self._pending_decision is not None:
            result = self._pending_decision
            self._pending_decision = None
            return result
        loop = asyncio.get_running_loop()
        self._future = loop.create_future()
        return await self._future

    def resolve(self, decision: ApprovalDecision) -> None:
        """Resolve the pending gate with the given decision."""
        if self._future is not None and not self._future.done():
            self._future.set_result(decision)
        else:
            self._pending_decision = decision


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

    Supports a single consumer only. Concurrent iteration over the same bus
    instance will cause one consumer to block indefinitely.
    """

    def __init__(self) -> None:
        self._queue: asyncio.Queue[str | object] = asyncio.Queue()
        self._closed = False

    async def emit(self, delta: str) -> None:
        """Emit a token delta to the stream."""
        if self._closed:
            raise RuntimeError("emit() called after close()")
        await self._queue.put(delta)

    def close(self) -> None:
        """Signal end-of-stream to consumers."""
        if self._closed:
            return
        self._closed = True
        self._queue.put_nowait(_SENTINEL)

    def __aiter__(self) -> AsyncIterator[str]:
        return self._iterate()

    async def _iterate(self) -> AsyncIterator[str]:
        if self._closed and self._queue.empty():
            return
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

    Supports a single consumer only. Concurrent iteration over the same bus
    instance will cause one consumer to block indefinitely.
    """

    def __init__(self) -> None:
        self._queue: asyncio.Queue[WikiContextEvent | object] = asyncio.Queue()
        self._closed = False

    async def emit(self, event: WikiContextEvent) -> None:
        """Emit a wiki context event."""
        if self._closed:
            raise RuntimeError("emit() called after close()")
        await self._queue.put(event)

    def close(self) -> None:
        """Signal end-of-stream to consumers."""
        if self._closed:
            return
        self._closed = True
        self._queue.put_nowait(_SENTINEL)

    def __aiter__(self) -> AsyncIterator[WikiContextEvent]:
        return self._iterate()

    async def _iterate(self) -> AsyncIterator[WikiContextEvent]:
        if self._closed and self._queue.empty():
            return
        while True:
            item = await self._queue.get()
            if item is _SENTINEL:
                break
            yield item  # type: ignore[misc]


@dataclass
class StatusEvent:
    """A structured status event describing pipeline progress.

    Emitted by the orchestrator at phase boundaries and key sub-steps so
    consumers (TUI, CLI) can render high-level activity without parsing
    raw token output.

    kind:
        - "phase_start": entering a new pipeline phase
        - "phase_end":   phase completed
        - "step":        a sub-step inside the active phase
        - "info":        informational note
        - "warn":        non-fatal issue
        - "error":       fatal error
        - "awaiting":    blocked on user input (approval gate)
    """

    phase: str
    message: str
    kind: str = "info"
    detail: str = ""


class StatusBus:
    """Async status event bus backed by asyncio.Queue.

    Producer: .emit(event) for each status event, .close() when done.
    Consumer: async iteration yields StatusEvent objects.

    Supports a single consumer only.
    """

    def __init__(self) -> None:
        self._queue: asyncio.Queue[StatusEvent | object] = asyncio.Queue()
        self._closed = False

    async def emit(self, event: StatusEvent) -> None:
        if self._closed:
            raise RuntimeError("emit() called after close()")
        await self._queue.put(event)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._queue.put_nowait(_SENTINEL)

    def __aiter__(self) -> AsyncIterator[StatusEvent]:
        return self._iterate()

    async def _iterate(self) -> AsyncIterator[StatusEvent]:
        if self._closed and self._queue.empty():
            return
        while True:
            item = await self._queue.get()
            if item is _SENTINEL:
                break
            yield item  # type: ignore[misc]


class NullStatusBus(StatusBus):
    """No-op status bus. Drops all events. Safe default for headless callers."""

    async def emit(self, event: StatusEvent) -> None:  # noqa: D401
        return None

    def close(self) -> None:
        self._closed = True

    def __aiter__(self) -> AsyncIterator[StatusEvent]:
        async def _empty() -> AsyncIterator[StatusEvent]:
            if False:
                yield  # type: ignore[unreachable]

        return _empty()
