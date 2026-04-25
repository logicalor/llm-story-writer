"""Unit tests for the pipeline orchestrator."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from application.pipeline.handoffs import (
    ApprovalDecision,
    ChapterDraft,
    OutlineResult,
    PipelineState,
    WikiUpdateBatch,
)
from domain.exceptions import StoryGenerationError
from presentation.pipeline_primitives import (
    ApprovalGate,
    NullApprovalGate,
    TokenStreamBus,
    WikiContextBus,
)
from presentation.orchestrator import (
    _load_savepoint,
    _write_savepoint,
    resume_pipeline,
    run_pipeline,
)


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


def _outline_result() -> OutlineResult:
    return OutlineResult(
        story_name="test-story",
        chapter_outlines=[
            {"chapter_number": 1, "title": "Chapter 1", "summary": "Intro"}
        ],
        summary="Story summary",
        genre="science fiction",
        themes=["memory"],
    )


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


class SequenceApprovalGate(ApprovalGate):
    def __init__(self, decisions: list[ApprovalDecision]) -> None:
        super().__init__()
        self._decisions = list(decisions)

    async def await_decision(self) -> ApprovalDecision:
        if not self._decisions:
            raise AssertionError("No more approval decisions configured")
        return self._decisions.pop(0)


@pytest.mark.asyncio
async def test_run_pipeline_happy_path(tmp_path: Path) -> None:
    provider = MagicMock()
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()

    def fake_savepoint_path(story_name: str) -> Path:
        return tmp_path / story_name / "savepoints" / "pipeline_state.json"

    with (
        patch(
            "presentation.orchestrator._savepoint_path", side_effect=fake_savepoint_path
        ),
        patch("presentation.orchestrator.OutlinePlannerAgent") as outline_cls,
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
    ):
        outline_cls.return_value.run = AsyncMock(return_value=_outline_result())
        chapter_cls.return_value.run = AsyncMock(return_value=_chapter_draft())
        wiki_cls.return_value.run = AsyncMock(return_value=_wiki_batch())
        consistency_cls.return_value.run = AsyncMock(
            return_value={"issues": [], "passed": True}
        )

        state = await run_pipeline(
            "test-story",
            NullApprovalGate(),
            bus,
            wiki_bus,
            config=_config(),
            provider=provider,
        )

    assert state.status == "complete"
    assert "init" in state.completed_phases
    assert "outline" in state.completed_phases
    assert len(state.savepoints) > 0


@pytest.mark.asyncio
async def test_chapter_files_written_during_chapter_loop(tmp_path: Path) -> None:
    provider = MagicMock()
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()

    def fake_savepoint_path(story_name: str) -> Path:
        return tmp_path / story_name / "savepoints" / "pipeline_state.json"

    with (
        patch(
            "presentation.orchestrator._savepoint_path", side_effect=fake_savepoint_path
        ),
        patch("presentation.orchestrator.STORIES_DIR", tmp_path),
        patch("tools._io.STORIES_DIR", tmp_path),
        patch("presentation.orchestrator.OutlinePlannerAgent") as outline_cls,
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
    ):
        outline_cls.return_value.run = AsyncMock(return_value=_outline_result())
        chapter_cls.return_value.run = AsyncMock(return_value=_chapter_draft())
        wiki_cls.return_value.run = AsyncMock(return_value=_wiki_batch())
        consistency_cls.return_value.run = AsyncMock(
            return_value={"issues": [], "passed": True}
        )

        await run_pipeline(
            "test-story",
            NullApprovalGate(),
            bus,
            wiki_bus,
            config=_config(),
            provider=provider,
        )

    chapter_path = tmp_path / "test-story" / "chapters" / "chapter_1.md"
    assert chapter_path.exists()
    assert chapter_path.read_text(encoding="utf-8") == "Draft content"


@pytest.mark.asyncio
async def test_assembly_writes_output_story_md(tmp_path: Path) -> None:
    provider = MagicMock()
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()

    def fake_savepoint_path(story_name: str) -> Path:
        return tmp_path / story_name / "savepoints" / "pipeline_state.json"

    with (
        patch(
            "presentation.orchestrator._savepoint_path", side_effect=fake_savepoint_path
        ),
        patch("presentation.orchestrator.STORIES_DIR", tmp_path),
        patch("tools._io.STORIES_DIR", tmp_path),
        patch("presentation.orchestrator.OutlinePlannerAgent") as outline_cls,
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
    ):
        outline_cls.return_value.run = AsyncMock(return_value=_outline_result())
        chapter_cls.return_value.run = AsyncMock(return_value=_chapter_draft())
        wiki_cls.return_value.run = AsyncMock(return_value=_wiki_batch())
        consistency_cls.return_value.run = AsyncMock(
            return_value={"issues": [], "passed": True}
        )

        await run_pipeline(
            "test-story",
            NullApprovalGate(),
            bus,
            wiki_bus,
            config=_config(),
            provider=provider,
        )

    output_path = tmp_path / "test-story" / "output" / "story.md"
    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert content.strip()
    assert "Draft content" in content


@pytest.mark.asyncio
async def test_run_pipeline_outline_rejection(tmp_path: Path) -> None:
    provider = MagicMock()
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    gate = SequenceApprovalGate([ApprovalDecision(approved=False)])

    def fake_savepoint_path(story_name: str) -> Path:
        return tmp_path / story_name / "savepoints" / "pipeline_state.json"

    with (
        patch(
            "presentation.orchestrator._savepoint_path", side_effect=fake_savepoint_path
        ),
        patch("presentation.orchestrator.OutlinePlannerAgent") as outline_cls,
    ):
        outline_cls.return_value.run = AsyncMock(return_value=_outline_result())

        state = await run_pipeline(
            "test-story",
            gate,
            bus,
            wiki_bus,
            config=_config(),
            provider=provider,
        )

    assert state.status == "rejected"
    assert "init" in state.completed_phases
    assert "chapter-loop" not in state.completed_phases


@pytest.mark.asyncio
async def test_run_pipeline_chapter_revision(tmp_path: Path) -> None:
    provider = MagicMock()
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    gate = SequenceApprovalGate(
        [
            ApprovalDecision(approved=True),
            ApprovalDecision(approved=False, feedback="needs more detail"),
            ApprovalDecision(approved=True),
        ]
    )

    def fake_savepoint_path(story_name: str) -> Path:
        return tmp_path / story_name / "savepoints" / "pipeline_state.json"

    with (
        patch(
            "presentation.orchestrator._savepoint_path", side_effect=fake_savepoint_path
        ),
        patch("presentation.orchestrator.OutlinePlannerAgent") as outline_cls,
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
    ):
        outline_cls.return_value.run = AsyncMock(return_value=_outline_result())
        chapter_cls.return_value.run = AsyncMock(
            side_effect=[_chapter_draft(), _chapter_draft()]
        )
        wiki_cls.return_value.run = AsyncMock(return_value=_wiki_batch())
        consistency_cls.return_value.run = AsyncMock(
            return_value={"issues": [], "passed": True}
        )

        state = await run_pipeline(
            "test-story",
            gate,
            bus,
            wiki_bus,
            config=_config(),
            provider=provider,
        )

        assert chapter_cls.return_value.run.await_count >= 2

    assert state.status == "complete"


@pytest.mark.asyncio
async def test_resume_pipeline_from_savepoint(tmp_path: Path) -> None:
    provider = MagicMock()
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    partial_state = PipelineState(
        story_name="test-story",
        current_phase="chapter-1",
        completed_phases=["init", "outline", "characters", "settings"],
        outline_result=_outline_result(),
        status="running",
        savepoints=["init", "outline", "characters", "settings"],
    )

    def fake_savepoint_path(story_name: str) -> Path:
        return tmp_path / story_name / "savepoints" / "pipeline_state.json"

    with patch(
        "presentation.orchestrator._savepoint_path", side_effect=fake_savepoint_path
    ):
        await _write_savepoint(partial_state)
        loaded_state = await _load_savepoint("test-story")

    assert loaded_state is not None
    assert loaded_state.current_phase == "chapter-1"

    with (
        patch(
            "presentation.orchestrator._savepoint_path", side_effect=fake_savepoint_path
        ),
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
    ):
        chapter_cls.return_value.run = AsyncMock(return_value=_chapter_draft())
        wiki_cls.return_value.run = AsyncMock(return_value=_wiki_batch())
        consistency_cls.return_value.run = AsyncMock(
            return_value={"issues": [], "passed": True}
        )

        state = await resume_pipeline(
            "test-story",
            None,
            NullApprovalGate(),
            bus,
            wiki_bus,
            config=_config(),
            provider=provider,
        )

    assert state.status == "complete"
    assert "chapter-loop" in state.completed_phases
    assert any(savepoint.startswith("chapter-") for savepoint in state.savepoints)


@pytest.mark.asyncio
async def test_assembly_raises_when_no_chapters(tmp_path: Path) -> None:
    provider = MagicMock()
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    partial_state = PipelineState(
        story_name="test-story",
        current_phase="assembly",
        completed_phases=[
            "init",
            "outline",
            "characters",
            "settings",
            "chapter-loop",
            "final-edit",
        ],
        outline_result=_outline_result(),
        approved_chapters=[],
        status="running",
        savepoints=[
            "init",
            "outline",
            "characters",
            "settings",
            "chapter-loop",
            "final-edit",
        ],
    )

    def fake_savepoint_path(story_name: str) -> Path:
        return tmp_path / story_name / "savepoints" / "pipeline_state.json"

    with (
        patch(
            "presentation.orchestrator._savepoint_path", side_effect=fake_savepoint_path
        ),
        patch("presentation.orchestrator.STORIES_DIR", tmp_path),
        patch("tools._io.STORIES_DIR", tmp_path),
    ):
        await _write_savepoint(partial_state)

        with pytest.raises(
            StoryGenerationError,
            match="Assembly failed: no approved chapter content to assemble",
        ):
            await resume_pipeline(
                "test-story",
                None,
                NullApprovalGate(),
                bus,
                wiki_bus,
                config=_config(),
                provider=provider,
            )
