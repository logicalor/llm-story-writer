import asyncio
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from application.pipeline.handoffs import ApprovalDecision
from presentation.pipeline_primitives import (
    ApprovalGate,
    NullApprovalGate,
    TokenStreamBus,
    WikiContextBus,
    WikiContextEvent,
)


def test_approval_gate_block_resolve() -> None:
    gate = ApprovalGate()
    expected = ApprovalDecision(approved=False, feedback="needs revision")

    async def resolve_later() -> None:
        await asyncio.sleep(0.01)
        gate.resolve(expected)

    async def main() -> ApprovalDecision:
        _, decision = await asyncio.gather(resolve_later(), gate.await_decision())
        return decision

    decision = asyncio.run(main())

    assert decision == expected


def test_null_approval_gate_returns_approve_immediately() -> None:
    gate = NullApprovalGate()

    decision = asyncio.run(gate.await_decision())

    assert decision.approved is True
    assert decision.auto_approved is True


def test_token_stream_bus_ordering() -> None:
    bus = TokenStreamBus()

    async def main() -> list[str]:
        await bus.emit("hello")
        await bus.emit(" world")
        await bus.emit("!")
        bus.close()

        return [delta async for delta in bus]

    assert asyncio.run(main()) == ["hello", " world", "!"]


def test_wiki_context_bus_ordering() -> None:
    bus = WikiContextBus()
    emitted = [
        WikiContextEvent(
            phase="entity-match",
            event_type="entity_match",
            content="Matched captain-vela",
        ),
        WikiContextEvent(
            phase="detail-level",
            event_type="detail_level",
            content="Selected L2 detail",
        ),
    ]

    async def main() -> list[WikiContextEvent]:
        for event in emitted:
            await bus.emit(event)
        bus.close()

        return [event async for event in bus]

    received = asyncio.run(main())

    assert [event.phase for event in received] == [event.phase for event in emitted]
    assert [event.event_type for event in received] == [
        event.event_type for event in emitted
    ]
    assert [event.content for event in received] == [event.content for event in emitted]


def test_close_before_consume() -> None:
    bus = TokenStreamBus()

    async def main() -> list[str]:
        await bus.emit("a")
        await bus.emit("b")
        bus.close()

        return [delta async for delta in bus]

    assert asyncio.run(main()) == ["a", "b"]


def test_close_mid_consume() -> None:
    bus = WikiContextBus()
    emitted = WikiContextEvent(
        phase="wikilink-traversal",
        event_type="wikilink_traversal",
        content="Traversed captain-vela -> rift-gate",
    )

    async def produce() -> None:
        await bus.emit(emitted)
        bus.close()

    async def consume() -> list[WikiContextEvent]:
        return [event async for event in bus]

    async def main() -> list[WikiContextEvent]:
        _, received = await asyncio.gather(produce(), consume())
        return received

    received = asyncio.run(main())

    assert len(received) == 1
    assert received[0].phase == emitted.phase
    assert received[0].event_type == emitted.event_type
    assert received[0].content == emitted.content


def test_emit_after_close_raises() -> None:
    token_bus = TokenStreamBus()
    token_bus.close()

    with pytest.raises(RuntimeError, match=r"emit\(\) called after close\(\)"):
        asyncio.run(token_bus.emit("x"))

    wiki_bus = WikiContextBus()
    wiki_bus.close()

    with pytest.raises(RuntimeError, match=r"emit\(\) called after close\(\)"):
        asyncio.run(
            wiki_bus.emit(
                WikiContextEvent(
                    phase="detail-level",
                    event_type="detail_level",
                    content="closed",
                )
            )
        )


def test_resolve_before_await_decision_returns_decision() -> None:
    gate = ApprovalGate()
    expected = ApprovalDecision(approved=True, feedback="pre-resolved")

    gate.resolve(expected)

    decision = asyncio.run(gate.await_decision())

    assert decision == expected
    assert decision.approved is True
    assert decision.feedback == "pre-resolved"


def test_close_idempotent() -> None:
    bus = TokenStreamBus()

    async def main() -> list[str]:
        await bus.emit("x")
        bus.close()
        bus.close()

        return [delta async for delta in bus]

    assert asyncio.run(main()) == ["x"]
