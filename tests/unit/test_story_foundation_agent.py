from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from application.pipeline.handoffs import OutlineResult
from domain.value_objects.generation_settings import GenerationSettings
from presentation.agents.story_foundation import StoryFoundationAgent


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
async def test_run_returns_outline_result_with_foundation_fields() -> None:
    provider = _ProviderStub(["context", "2024-01-15", "elements"])
    bus = _StubBus()
    wiki_bus = _StubWikiBus()
    agent = StoryFoundationAgent(provider, {}, bus, wiki_bus)

    with patch(
        "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
        side_effect=lambda name, variables=None: f"prompt::{name}",
    ):
        result = await agent.run(
            "my-story",
            "a story prompt",
            GenerationSettings.from_dict({}),
        )

    assert isinstance(result, OutlineResult)
    assert result.base_context == "context"
    assert result.story_start_date == "2024-01-15"
    assert result.story_elements == "elements"
    assert result.story_name == "my-story"


@pytest.mark.asyncio
async def test_run_graceful_degradation_on_first_call_failure() -> None:
    provider = _ProviderStub([Exception("boom"), "2024-01-15", "elements"])
    bus = _StubBus()
    wiki_bus = _StubWikiBus()
    agent = StoryFoundationAgent(provider, {}, bus, wiki_bus)

    with patch(
        "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
        side_effect=lambda name, variables=None: f"prompt::{name}",
    ):
        result = await agent.run(
            "my-story",
            "a story prompt",
            GenerationSettings.from_dict({}),
        )

    assert result.base_context == ""
    assert result.story_start_date == "2024-01-15"
    assert result.story_elements == "elements"


@pytest.mark.asyncio
async def test_run_graceful_degradation_on_all_calls_failure() -> None:
    provider = _ProviderStub(Exception("boom"))
    bus = _StubBus()
    wiki_bus = _StubWikiBus()
    agent = StoryFoundationAgent(provider, {}, bus, wiki_bus)

    with patch(
        "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
        side_effect=lambda name, variables=None: f"prompt::{name}",
    ):
        result = await agent.run(
            "my-story",
            "a story prompt",
            GenerationSettings.from_dict({}),
        )

    assert result.base_context == ""
    assert result.story_start_date == ""
    assert result.story_elements == ""


@pytest.mark.asyncio
async def test_run_emits_foundation_status_to_bus() -> None:
    provider = _ProviderStub(["context", "2024-01-15", "elements"])
    bus = _StubBus()
    wiki_bus = _StubWikiBus()
    agent = StoryFoundationAgent(provider, {}, bus, wiki_bus)

    with patch(
        "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
        side_effect=lambda name, variables=None: f"prompt::{name}",
    ):
        await agent.run(
            "my-story",
            "a story prompt",
            GenerationSettings.from_dict({}),
        )

    assert any("[Foundation]" in message for message in bus.messages)
