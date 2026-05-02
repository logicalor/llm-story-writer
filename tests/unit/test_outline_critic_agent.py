from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from application.pipeline.handoffs import (
    ArcAnalysisResult,
    ChapterDraft,
    OutlineResult,
    PipelineState,
    StoryMetadataResult,
    WikiUpdateBatch,
)
from domain.value_objects.generation_settings import GenerationSettings
from presentation.agents.outline_critic import OUTLINE_CRITIC_TYPES, OutlineCriticAgent
from presentation.orchestrator import _continue_pipeline
from presentation.pipeline_primitives import NullApprovalGate
from tools.critique_parser import CritiqueResult


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
    def __init__(self) -> None:
        self.generate_text = AsyncMock(side_effect=self._generate_text)

    async def _generate_text(self, messages, model_config, seed):  # type: ignore[no-untyped-def]
        prompt_name = messages[-1]["content"].removeprefix("prompt::")
        if prompt_name.startswith("outline_review/"):
            critic_type = prompt_name.split("/", 1)[1]
            return f"critique::{critic_type}"
        if prompt_name == "outline_arc/arc_distribution":
            return "arc distribution response"
        if prompt_name == "outline_arc/promise_payoff":
            return "promise payoff response"
        if prompt_name == "outline_arc/arc_synthesis":
            return "arc synthesis response"
        raise AssertionError(f"Unexpected prompt: {prompt_name}")


def _outline_result() -> OutlineResult:
    return OutlineResult(
        story_name="test-story",
        chapter_outlines=[
            {"chapter_number": 1, "title": "Chapter 1", "summary": "Intro"}
        ],
        chapter_details=[{"chapter_number": 1, "detail": "Extra detail"}],
        summary="Story summary",
        genre="science fiction",
        themes=["memory"],
    )


def _state() -> PipelineState:
    return PipelineState(
        story_name="test-story",
        current_phase="outline",
        outline_result=_outline_result(),
    )


def _settings(**updates: object) -> GenerationSettings:
    return GenerationSettings.from_dict(updates)


def _make_agent(provider: _ProviderStub) -> OutlineCriticAgent:
    return OutlineCriticAgent(provider, {}, _StubBus(), _StubWikiBus())


def _critique_result(critic_type: str) -> CritiqueResult:
    return CritiqueResult(
        critic_type=critic_type,
        scores=[],
        summary=f"summary::{critic_type}",
        overall_score=90.0,
    )


def _expected_critic_summary() -> str:
    return "\n\n".join(f"summary::{critic_type}" for critic_type in OUTLINE_CRITIC_TYPES)


def _config() -> dict[str, object]:
    return {
        "generation": {"wanted_chapters": 1, "seed": 12},
        "models": {
            "initial_outline_writer": "openai-compat://outline-model",
            "chapter_writer": "openai-compat://chapter-model",
            "checker_model": "openai-compat://checker-model",
            "eval_model": "openai-compat://wiki-model",
        },
        "model_api_base": "http://127.0.0.1:1234/v1",
        "context_length": 16384,
        "randomize_seed": False,
    }


def _chapter_draft() -> ChapterDraft:
    return ChapterDraft(
        story_name="test-story",
        chapter_number=1,
        title="Chapter 1",
        content="Draft content",
        word_count=2,
    )


def _wiki_batch() -> WikiUpdateBatch:
    return WikiUpdateBatch(
        story_name="test-story",
        chapter_number=1,
        updated_pages=[],
        new_pages=[],
    )


def _story_metadata_result() -> StoryMetadataResult:
    return StoryMetadataResult(
        story_name="test-story",
        title="Title",
        summary="Summary",
        tags=["tag"],
    )


@pytest.mark.asyncio
async def test_critic_pass_runs_six_critics_sequentially(tmp_path: Path) -> None:
    provider = _ProviderStub()
    agent = _make_agent(provider)

    with (
        patch("presentation.agents.outline_critic.STORIES_DIR", tmp_path),
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            side_effect=lambda name, variables=None: f"prompt::{name}",
        ),
        patch.object(
            agent._parser,
            "parse_critique",
            side_effect=lambda critic_type, response: _critique_result(critic_type),
        ),
    ):
        result = await agent.run(_state(), _settings(enable_concurrent_critics=False))

    assert provider.generate_text.call_count == 9
    assert result.critic_summary == "arc synthesis response"


@pytest.mark.asyncio
async def test_critic_pass_runs_six_critics_concurrently(tmp_path: Path) -> None:
    provider = _ProviderStub()
    agent = _make_agent(provider)

    with (
        patch("presentation.agents.outline_critic.STORIES_DIR", tmp_path),
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            side_effect=lambda name, variables=None: f"prompt::{name}",
        ),
        patch.object(
            agent._parser,
            "parse_critique",
            side_effect=lambda critic_type, response: _critique_result(critic_type),
        ),
    ):
        result = await agent.run(_state(), _settings(enable_concurrent_critics=True))

    assert provider.generate_text.call_count == 9
    assert result.critic_summary == "arc synthesis response"


@pytest.mark.asyncio
async def test_critic_summary_persisted_to_state(tmp_path: Path) -> None:
    provider = _ProviderStub()
    agent = _make_agent(provider)

    with (
        patch("presentation.agents.outline_critic.STORIES_DIR", tmp_path),
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            side_effect=lambda name, variables=None: f"prompt::{name}",
        ),
        patch.object(
            agent._parser,
            "parse_critique",
            side_effect=lambda critic_type, response: _critique_result(critic_type),
        ),
    ):
        result = await agent.run(_state(), _settings())

    assert result.critic_summary == "arc synthesis response"


@pytest.mark.asyncio
async def test_arc_fields_persisted_to_state(tmp_path: Path) -> None:
    provider = _ProviderStub()
    agent = _make_agent(provider)

    with (
        patch("presentation.agents.outline_critic.STORIES_DIR", tmp_path),
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            side_effect=lambda name, variables=None: f"prompt::{name}",
        ),
        patch.object(
            agent._parser,
            "parse_critique",
            side_effect=lambda critic_type, response: _critique_result(critic_type),
        ),
    ):
        result = await agent.run(_state(), _settings())

    assert result.arc_distribution == "arc distribution response"
    assert result.promise_payoff == "promise payoff response"


@pytest.mark.asyncio
async def test_critic_summary_written_to_disk(tmp_path: Path) -> None:
    provider = _ProviderStub()
    agent = _make_agent(provider)

    with (
        patch("presentation.agents.outline_critic.STORIES_DIR", tmp_path),
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            side_effect=lambda name, variables=None: f"prompt::{name}",
        ),
        patch.object(
            agent._parser,
            "parse_critique",
            side_effect=lambda critic_type, response: _critique_result(critic_type),
        ),
    ):
        await agent.run(_state(), _settings())

    critic_summary_path = tmp_path / "test-story" / "outline" / "critic_summary.md"
    assert critic_summary_path.exists()
    assert critic_summary_path.read_text(encoding="utf-8") == _expected_critic_summary()


@pytest.mark.asyncio
async def test_outline_critique_disabled_skips_critics(tmp_path: Path) -> None:
    provider = MagicMock()
    provider.generate_text = AsyncMock()
    provider.stream_text = MagicMock()

    def fake_savepoint_path(story_name: str) -> Path:
        return tmp_path / story_name / "savepoints" / "pipeline_state.json"

    with (
        patch(
            "presentation.orchestrator._savepoint_path",
            side_effect=fake_savepoint_path,
        ),
        patch("presentation.orchestrator.STORIES_DIR", tmp_path),
        patch("tools._io.STORIES_DIR", tmp_path),
        patch("presentation.orchestrator.OutlinePlannerAgent") as outline_cls,
        patch("presentation.orchestrator.OutlineCriticAgent") as critic_cls,
        patch(
            "presentation.orchestrator._await_outline_approval",
            new=AsyncMock(side_effect=lambda state, *args, **kwargs: state),
        ),
    ):
        outline_cls.return_value.run = AsyncMock(return_value=_outline_result())
        state = await _continue_pipeline(
            PipelineState(
                story_name="test-story",
                current_phase="outline",
                completed_phases=[
                    "story-foundation",
                    "metadata-outline",
                    "narrative-arc",
                    "characters",
                    "settings",
                    "wiki-bootstrap",
                    "chapter-loop",
                    "final-edit",
                    "metadata-final",
                    "assembly",
                ],
            ),
            NullApprovalGate(),
            _StubBus(),
            _StubWikiBus(),
            config={
                **_config(),
                "generation": {
                    "wanted_chapters": 1,
                    "seed": 12,
                    "enable_outline_critique": False,
                },
            },
            provider=provider,
        )

    critic_cls.assert_not_called()
    assert provider.generate_text.call_count == 0
    assert provider.stream_text.call_count == 0
    assert state.critic_summary == ""
    assert state.arc_distribution == ""
    assert state.promise_payoff == ""


@pytest.mark.asyncio
async def test_completed_phases_updated(tmp_path: Path) -> None:
    provider = _ProviderStub()
    agent = _make_agent(provider)

    with (
        patch("presentation.agents.outline_critic.STORIES_DIR", tmp_path),
        patch(
            "infrastructure.prompts.prompt_loader.PromptLoader.load_prompt",
            side_effect=lambda name, variables=None: f"prompt::{name}",
        ),
        patch.object(
            agent._parser,
            "parse_critique",
            side_effect=lambda critic_type, response: _critique_result(critic_type),
        ),
    ):
        result = await agent.run(_state(), _settings())

    assert "outline-critique" in result.completed_phases