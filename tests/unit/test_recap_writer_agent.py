from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from domain.value_objects.generation_settings import GenerationSettings
from presentation.agents.recap_writer import RecapWriterAgent


class _StubBus:
    def __init__(self) -> None:
        self.messages: list[str] = []

    async def emit(self, msg: str) -> None:
        self.messages.append(msg)

    def close(self) -> None:
        pass


class _StubWikiBus:
    def __init__(self) -> None:
        self.events: list[object] = []

    async def emit(self, event: object) -> None:
        self.events.append(event)

    def close(self) -> None:
        pass


class _ProviderStub:
    def __init__(self, side_effect: object) -> None:
        self.generate_text = AsyncMock(side_effect=side_effect)


@pytest.mark.asyncio
async def test_run_full_path_returns_events_compact_sanitised() -> None:
    provider = _ProviderStub(
        [
            "events text",
            "timed events",
            "enriched events",
            '{"events": ["formatted"]}',
            "compact recap",
            "sanitised recap",
        ]
    )
    bus = _StubBus()
    wiki_bus = _StubWikiBus()
    agent = RecapWriterAgent(provider, {}, bus, wiki_bus)

    with patch(
        "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
        side_effect=lambda name, variables=None: f"prompt::{name}",
    ):
        result = await agent.run(
            "my-story",
            3,
            "chapter body",
            "previous recap",
            "2024-01-15",
            GenerationSettings.from_dict({}),
        )

    assert result == {
        "events": "events text",
        "compact": "compact recap",
        "sanitised": "sanitised recap",
    }
    assert provider.generate_text.call_count == 6


@pytest.mark.asyncio
async def test_run_short_path_two_calls() -> None:
    provider = _ProviderStub(["events text", '{"events": ["formatted"]}'])
    bus = _StubBus()
    wiki_bus = _StubWikiBus()
    agent = RecapWriterAgent(provider, {}, bus, wiki_bus)

    with patch(
        "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
        side_effect=lambda name, variables=None: f"prompt::{name}",
    ):
        result = await agent.run(
            "my-story",
            3,
            "chapter body",
            "previous recap",
            "2024-01-15",
            GenerationSettings.from_dict(
                {
                    "use_multi_stage_recap_sanitizer": False,
                }
            ),
        )

    assert provider.generate_text.call_count == 2
    assert result["events"] == "events text"
    assert result["compact"] == '{"events": ["formatted"]}'
    assert result["sanitised"] == result["compact"]


@pytest.mark.asyncio
async def test_run_skip_sanitizer_five_calls() -> None:
    provider = _ProviderStub(
        [
            "events text",
            "timed events",
            "enriched events",
            '{"events": ["formatted"]}',
            "compact recap",
        ]
    )
    bus = _StubBus()
    wiki_bus = _StubWikiBus()
    agent = RecapWriterAgent(provider, {}, bus, wiki_bus)

    with patch(
        "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
        side_effect=lambda name, variables=None: f"prompt::{name}",
    ):
        result = await agent.run(
            "my-story",
            3,
            "chapter body",
            "previous recap",
            "2024-01-15",
            GenerationSettings.from_dict(
                {
                    "use_improved_recap_sanitizer": False,
                }
            ),
        )

    assert provider.generate_text.call_count == 5
    assert result["events"] == "events text"
    assert result["compact"] == "compact recap"
    assert result["sanitised"] == result["compact"]


@pytest.mark.asyncio
async def test_run_stage1_failure_returns_empty_dict() -> None:
    provider = _ProviderStub(Exception("boom"))
    bus = _StubBus()
    wiki_bus = _StubWikiBus()
    agent = RecapWriterAgent(provider, {}, bus, wiki_bus)

    with patch(
        "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
        side_effect=lambda name, variables=None: f"prompt::{name}",
    ):
        result = await agent.run(
            "my-story",
            3,
            "chapter body",
            "previous recap",
            "2024-01-15",
            GenerationSettings.from_dict({}),
        )

    assert result == {
        "events": "",
        "compact": "",
        "sanitised": "",
    }


@pytest.mark.asyncio
async def test_run_emits_stage_messages_to_bus() -> None:
    provider = _ProviderStub(
        [
            "events text",
            "timed events",
            "enriched events",
            '{"events": ["formatted"]}',
            "compact recap",
            "sanitised recap",
        ]
    )
    bus = _StubBus()
    wiki_bus = _StubWikiBus()
    agent = RecapWriterAgent(provider, {}, bus, wiki_bus)

    with patch(
        "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
        side_effect=lambda name, variables=None: f"prompt::{name}",
    ):
        await agent.run(
            "my-story",
            3,
            "chapter body",
            "previous recap",
            "2024-01-15",
            GenerationSettings.from_dict({}),
        )

    assert any("[Recap]" in message for message in bus.messages)


@pytest.mark.asyncio
async def test_run_accepts_empty_previous_recap_and_start_date() -> None:
    provider = _ProviderStub(
        [
            "events text",
            "timed events",
            "enriched events",
            '{"events": ["formatted"]}',
            "compact recap",
            "sanitised recap",
        ]
    )
    bus = _StubBus()
    wiki_bus = _StubWikiBus()
    agent = RecapWriterAgent(provider, {}, bus, wiki_bus)

    with patch(
        "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
        side_effect=lambda name, variables=None: f"prompt::{name}",
    ):
        result = await agent.run(
            "my-story",
            3,
            "chapter body",
            "",
            "",
            GenerationSettings.from_dict({}),
        )

    assert isinstance(result, dict)
    assert result["events"] == "events text"
