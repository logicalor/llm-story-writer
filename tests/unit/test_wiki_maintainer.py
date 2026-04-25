import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from application.pipeline.handoffs import WikiUpdateBatch
from presentation.agents.wiki_maintainer import WikiMaintainerAgent
from presentation.pipeline_primitives import WikiContextEvent


_FAKE_SUMMARY = {
    "created": 2,
    "updated": 1,
    "timeline_events": 0,
    "entity_counts": {},
    "new_slugs": ["priya", "ember-port"],
    "updated_slugs": ["vale"],
}


class _CollectingWikiBus:
    def __init__(self) -> None:
        self.events: list[WikiContextEvent] = []

    async def emit(self, event: WikiContextEvent) -> None:
        self.events.append(event)

    def close(self) -> None:
        pass


class _CollectingBus:
    def __init__(self) -> None:
        self.tokens: list[str] = []

    async def emit(self, token: str) -> None:
        self.tokens.append(token)

    def close(self) -> None:
        pass


class _UnexpectedProvider:
    async def stream_text(self, messages, model_config):
        pytest.fail("provider.stream_text should not be called")
        return
        yield


def _build_agent(
    config: dict[str, object] | None = None,
    provider: object | None = None,
) -> tuple[WikiMaintainerAgent, _CollectingWikiBus]:
    wiki_bus = _CollectingWikiBus()
    agent = WikiMaintainerAgent(
        provider=provider or MagicMock(),
        config=config or {},
        bus=_CollectingBus(),
        wiki_bus=wiki_bus,
    )
    return agent, wiki_bus


@pytest.mark.asyncio
async def test_run_returns_populated_wiki_update_batch() -> None:
    agent, _ = _build_agent()

    with patch(
        "presentation.agents.wiki_maintainer.update_wiki_from_chapter",
        return_value=_FAKE_SUMMARY,
    ):
        result = await agent.run("test-story", 3, "Chapter text")

    assert isinstance(result, WikiUpdateBatch)
    assert result.story_name == "test-story"
    assert result.chapter_number == 3
    assert result.new_pages == ["priya", "ember-port"]
    assert result.updated_pages == ["vale"]
    assert result.savepoint_id is None


@pytest.mark.asyncio
async def test_run_emits_wiki_context_events_for_each_page() -> None:
    agent, wiki_bus = _build_agent()
    summary = {
        "created": 1,
        "updated": 1,
        "timeline_events": 0,
        "entity_counts": {},
        "new_slugs": ["priya"],
        "updated_slugs": ["vale"],
    }

    with patch(
        "presentation.agents.wiki_maintainer.update_wiki_from_chapter",
        return_value=summary,
    ):
        await agent.run("test-story", 2, "Chapter text")

    assert len(wiki_bus.events) == 3
    assert wiki_bus.events[0] == WikiContextEvent(
        phase="wiki",
        event_type="wikilink_traversal",
        content="Processing chapter 2 wiki updates",
    )
    assert wiki_bus.events[1] == WikiContextEvent(
        phase="wiki",
        event_type="entity_match",
        content="Created wiki page: priya",
        metadata={"slug": "priya", "action": "create"},
    )
    assert wiki_bus.events[2] == WikiContextEvent(
        phase="wiki",
        event_type="entity_match",
        content="Updated wiki page: vale",
        metadata={"slug": "vale", "action": "update"},
    )


@pytest.mark.asyncio
async def test_run_no_pages_returns_empty_batch() -> None:
    agent, wiki_bus = _build_agent()
    summary = {
        "created": 0,
        "updated": 0,
        "timeline_events": 0,
        "entity_counts": {},
        "new_slugs": [],
        "updated_slugs": [],
    }

    with patch(
        "presentation.agents.wiki_maintainer.update_wiki_from_chapter",
        return_value=summary,
    ):
        result = await agent.run("test-story", 4, "Chapter text")

    assert result == WikiUpdateBatch(
        story_name="test-story",
        chapter_number=4,
        updated_pages=[],
        new_pages=[],
        savepoint_id=None,
    )
    assert wiki_bus.events == [
        WikiContextEvent(
            phase="wiki",
            event_type="wikilink_traversal",
            content="Processing chapter 4 wiki updates",
        )
    ]


@pytest.mark.asyncio
async def test_run_does_not_call_provider_stream_text() -> None:
    agent, _ = _build_agent(provider=_UnexpectedProvider())

    with patch(
        "presentation.agents.wiki_maintainer.update_wiki_from_chapter",
        return_value=_FAKE_SUMMARY,
    ):
        await agent.run("test-story", 1, "Chapter text")


@pytest.mark.asyncio
async def test_run_uses_model_config_from_eval_model() -> None:
    agent, _ = _build_agent(
        config={"models": {"eval_model": "openai-compat://my-model"}}
    )

    with patch(
        "presentation.agents.wiki_maintainer.update_wiki_from_chapter",
        return_value=_FAKE_SUMMARY,
    ) as mock_update:
        await agent.run("test-story", 5, "Chapter text")

    mock_update.assert_called_once_with(
        "test-story",
        5,
        "Chapter text",
        model="my-model",
    )
