"""Unit tests for the pipeline orchestrator."""

import json
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
    ArcAnalysisResult,
    ChapterDraft,
    FinalEditResult,
    OutlineResult,
    PipelineState,
    StoryMetadataResult,
    WikiUpdateBatch,
)
from domain.exceptions import StoryGenerationError
from presentation.pipeline_primitives import (
    ApprovalGate,
    NullApprovalGate,
    StatusBus,
    TokenStreamBus,
    WikiContextBus,
)
from presentation.orchestrator import (
    _generate_character_sheets,
    _generate_setting_sheets,
    _load_savepoint,
    _mark_work_item_done,
    _work_item_done,
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


def _story_metadata_result() -> StoryMetadataResult:
    return StoryMetadataResult(
        story_name="test-story",
        title="Title",
        summary="Summary",
        tags=["tag"],
    )


def _two_chapter_outline_result() -> OutlineResult:
    return OutlineResult(
        story_name="test-story",
        chapter_outlines=[
            {"chapter_number": 1, "title": "Chapter 1", "summary": "Intro"},
            {"chapter_number": 2, "title": "Chapter 2", "summary": "Turn"},
        ],
        summary="Story summary",
        genre="science fiction",
        themes=["memory"],
    )


def _wiki_batch() -> WikiUpdateBatch:
    return WikiUpdateBatch(
        story_name="test-story",
        chapter_number=1,
        updated_pages=[],
        new_pages=[],
    )


def _generated_character_paths() -> list[Path]:
    return [Path("characters/alice.json")]


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
        patch("presentation.orchestrator.STORIES_DIR", tmp_path),
        patch("tools._io.STORIES_DIR", tmp_path),
        patch("presentation.orchestrator.OutlinePlannerAgent") as outline_cls,
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
        patch(
            "presentation.orchestrator._generate_character_sheets",
            new=AsyncMock(return_value=_generated_character_paths()),
        ),
        patch(
            "presentation.orchestrator._generate_setting_sheets",
            new=AsyncMock(return_value=[]),
        ),
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
async def test_wiki_update_failure_does_not_abort_chapter_loop(
    tmp_path: Path,
) -> None:
    """Regression: wiki update failures must not lose the approved chapter or
    stop the chapter loop. The chapter remains in approved_chapters and the
    pipeline continues to completion."""
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
        patch("presentation.orchestrator.StoryFoundationAgent") as foundation_cls,
        patch("presentation.orchestrator.OutlinePlannerAgent") as outline_cls,
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
        patch(
            "presentation.orchestrator._generate_character_sheets",
            new=AsyncMock(return_value=_generated_character_paths()),
        ),
        patch(
            "presentation.orchestrator._generate_setting_sheets",
            new=AsyncMock(return_value=[]),
        ),
    ):
        foundation_cls.return_value.run = AsyncMock(return_value=_outline_result())
        outline_cls.return_value.run = AsyncMock(return_value=_outline_result())
        chapter_cls.return_value.run = AsyncMock(return_value=_chapter_draft())
        wiki_cls.return_value.run = AsyncMock(
            side_effect=RuntimeError("wiki backend down")
        )
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
    assert len(state.approved_chapters) == 1
    # No wiki batch persisted because the update failed, but pipeline finished.
    assert state.wiki_batches == []


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
        patch(
            "presentation.orchestrator._generate_character_sheets",
            new=AsyncMock(return_value=_generated_character_paths()),
        ),
        patch(
            "presentation.orchestrator._generate_setting_sheets",
            new=AsyncMock(return_value=[]),
        ),
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
        patch("presentation.orchestrator.StoryFoundationAgent") as foundation_cls,
        patch("presentation.orchestrator.OutlinePlannerAgent") as outline_cls,
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
        patch(
            "presentation.orchestrator._generate_character_sheets",
            new=AsyncMock(return_value=_generated_character_paths()),
        ),
        patch(
            "presentation.orchestrator._generate_setting_sheets",
            new=AsyncMock(return_value=[]),
        ),
    ):
        foundation_cls.return_value.run = AsyncMock(return_value=_outline_result())
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
        patch(
            "presentation.orchestrator._generate_character_sheets",
            new=AsyncMock(return_value=_generated_character_paths()),
        ),
        patch(
            "presentation.orchestrator._generate_setting_sheets",
            new=AsyncMock(return_value=[]),
        ),
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
    # Rejected outline must NOT be marked complete, otherwise resume would
    # bypass the approval gate.
    assert "outline" not in state.completed_phases


@pytest.mark.asyncio
async def test_outline_revision_does_not_duplicate_savepoint(tmp_path: Path) -> None:
    provider = MagicMock()
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    gate = SequenceApprovalGate(
        [
            ApprovalDecision(approved=False, feedback="tighten the hook"),
            ApprovalDecision(approved=True),
            ApprovalDecision(approved=True),
        ]
    )

    def fake_savepoint_path(story_name: str) -> Path:
        return tmp_path / story_name / "savepoints" / "pipeline_state.json"

    with (
        patch(
            "presentation.orchestrator._savepoint_path", side_effect=fake_savepoint_path
        ),
        patch("presentation.orchestrator.STORIES_DIR", tmp_path),
        patch("tools._io.STORIES_DIR", tmp_path),
        patch("presentation.orchestrator.OutlinePlannerAgent") as outline_cls,
        patch("presentation.orchestrator.StoryPlannerAgent") as arc_cls,
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
        patch("presentation.orchestrator.FinalEditorAgent") as final_cls,
        patch(
            "presentation.orchestrator._generate_character_sheets",
            new=AsyncMock(return_value=_generated_character_paths()),
        ),
        patch(
            "presentation.orchestrator._generate_setting_sheets",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "presentation.orchestrator._init_wiki_for_story",
            return_value={"status": "ok"},
        ),
    ):
        outline_cls.return_value.run = AsyncMock(
            side_effect=[_outline_result(), _outline_result()]
        )
        arc_cls.return_value.run = AsyncMock(
            return_value=ArcAnalysisResult(
                story_name="test-story",
                arc_assessment="Strong arc",
                verdict_code="strong",
                overall_score=80.0,
            )
        )
        chapter_cls.return_value.run = AsyncMock(return_value=_chapter_draft())
        wiki_cls.return_value.run = AsyncMock(return_value=_wiki_batch())
        consistency_cls.return_value.run = AsyncMock(
            return_value={"issues": [], "passed": True}
        )
        final_cls.return_value.run = AsyncMock(
            return_value=FinalEditResult(
                story_name="test-story",
                chapters_processed=1,
                total_issues_found=0,
                total_revisions_made=0,
                edited_chapters=[_chapter_draft()],
            )
        )

        state = await run_pipeline(
            "test-story",
            gate,
            bus,
            wiki_bus,
            config=_config(),
            provider=provider,
        )

    assert state.status == "complete"
    assert state.savepoints.count("outline") == 1


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
        patch(
            "presentation.orchestrator._generate_character_sheets",
            new=AsyncMock(return_value=_generated_character_paths()),
        ),
        patch(
            "presentation.orchestrator._generate_setting_sheets",
            new=AsyncMock(return_value=[]),
        ),
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

    with (
        patch(
            "presentation.orchestrator._savepoint_path", side_effect=fake_savepoint_path
        ),
        patch("tools._io.STORIES_DIR", tmp_path),
    ):
        await _write_savepoint(partial_state)
        loaded_state = await _load_savepoint("test-story")

    assert loaded_state is not None
    assert loaded_state.current_phase == "chapter-1"

    with (
        patch(
            "presentation.orchestrator._savepoint_path", side_effect=fake_savepoint_path
        ),
        patch("presentation.orchestrator.STORIES_DIR", tmp_path),
        patch("tools._io.STORIES_DIR", tmp_path),
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
        patch(
            "presentation.orchestrator._generate_character_sheets",
            new=AsyncMock(return_value=_generated_character_paths()),
        ),
        patch(
            "presentation.orchestrator._generate_setting_sheets",
            new=AsyncMock(return_value=[]),
        ),
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
async def test_resume_pipeline_backfills_missing_chapter_files(tmp_path: Path) -> None:
    provider = MagicMock()
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    chapter_one = ChapterDraft(
        story_name="test-story",
        chapter_number=1,
        title="Chapter 1",
        content="Existing approved content",
        word_count=3,
    )
    chapter_two = ChapterDraft(
        story_name="test-story",
        chapter_number=2,
        title="Chapter 2",
        content="Missing approved content",
        word_count=3,
    )
    partial_state = PipelineState(
        story_name="test-story",
        current_phase="complete",
        completed_phases=[
            "init",
            "outline",
            "narrative-arc",
            "characters",
            "settings",
            "chapter-loop",
            "final-edit",
            "assembly",
        ],
        outline_result=_two_chapter_outline_result(),
        approved_chapters=[chapter_one, chapter_two],
        status="complete",
        savepoints=[
            "init",
            "outline",
            "arc_analysis_complete",
            "characters",
            "settings",
            "chapter-loop",
            "final_edit_complete",
            "assembly",
            "complete",
        ],
    )

    def fake_savepoint_path(story_name: str) -> Path:
        return tmp_path / story_name / "savepoints" / "pipeline_state.json"

    existing_chapter_path = tmp_path / "test-story" / "chapters" / "chapter_1.md"
    existing_chapter_path.parent.mkdir(parents=True, exist_ok=True)
    existing_chapter_path.write_text("Keep this chapter file\n", encoding="utf-8")

    with (
        patch(
            "presentation.orchestrator._savepoint_path", side_effect=fake_savepoint_path
        ),
        patch("presentation.orchestrator.STORIES_DIR", tmp_path),
        patch("tools._io.STORIES_DIR", tmp_path),
    ):
        await _write_savepoint(partial_state)

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
    assert (
        existing_chapter_path.read_text(encoding="utf-8") == "Keep this chapter file\n"
    )
    assert (tmp_path / "test-story" / "chapters" / "chapter_2.md").read_text(
        encoding="utf-8"
    ) == "Missing approved content"


@pytest.mark.asyncio
async def test_resume_pipeline_rejects_invalid_savepoint_name(tmp_path: Path) -> None:
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    partial_state = PipelineState(
        story_name="test-story",
        current_phase="outline",
        completed_phases=["init", "outline"],
        outline_result=_outline_result(),
        status="running",
        savepoints=["init", "outline"],
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
            match="Savepoint 'nonexistent' not found in story 'test-story'",
        ):
            await resume_pipeline(
                "test-story",
                "nonexistent",
                NullApprovalGate(),
                bus,
                wiki_bus,
            )


@pytest.mark.asyncio
async def test_resume_pipeline_accepts_valid_savepoint_name(tmp_path: Path) -> None:
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    partial_state = PipelineState(
        story_name="test-story",
        current_phase="outline",
        completed_phases=["init", "outline"],
        outline_result=_outline_result(),
        status="complete",
        savepoints=["init", "outline"],
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

        result = await resume_pipeline(
            "test-story",
            "outline",
            NullApprovalGate(),
            bus,
            wiki_bus,
        )

    assert isinstance(result, PipelineState)
    assert result.story_name == "test-story"
    assert "outline" in result.savepoints


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
        patch(
            "presentation.orchestrator._generate_character_sheets",
            new=AsyncMock(return_value=_generated_character_paths()),
        ),
        patch(
            "presentation.orchestrator._generate_setting_sheets",
            new=AsyncMock(return_value=[]),
        ),
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


@pytest.mark.asyncio
async def test_characters_phase_writes_sheets_to_disk(tmp_path: Path) -> None:
    """Characters phase writes character sheet JSON files to disk."""
    provider = MagicMock()
    provider.generate_text = AsyncMock(
        side_effect=[
            '["Alice", "Bob"]',
            "# Alice\nHero of the story.",
            *["chunk response"] * 7,
            "Alice abridged",
            "Alice summary",
            "# Bob\nSidekick.",
            *["chunk response"] * 7,
            "Bob abridged",
            "Bob summary",
        ]
    )
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
        patch("presentation.orchestrator.StoryFoundationAgent") as foundation_cls,
        patch("presentation.orchestrator.OutlinePlannerAgent") as outline_cls,
        patch("presentation.orchestrator.StoryMetadataAgent") as metadata_cls,
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
        patch(
            "presentation.orchestrator._generate_setting_sheets",
            new=AsyncMock(return_value=[]),
        ),
    ):
        foundation_cls.return_value.run = AsyncMock(return_value=_outline_result())
        outline_cls.return_value.run = AsyncMock(return_value=_outline_result())
        metadata_cls.return_value.run = AsyncMock(return_value=_story_metadata_result())
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

    characters_dir = tmp_path / "test-story" / "characters"
    assert characters_dir.exists()
    written = [p for p in characters_dir.glob("*.json") if p.name != "_names.json"]
    assert len(written) == 2
    names_written = {
        json.loads(path.read_text(encoding="utf-8"))["name"] for path in written
    }
    assert names_written == {"Alice", "Bob"}
    assert (characters_dir / "_names.json").exists()


@pytest.mark.asyncio
async def test_characters_phase_skips_failed_sheet_generation(tmp_path: Path) -> None:
    provider = MagicMock()
    provider.generate_text = AsyncMock(
        side_effect=[
            '["Alice", "Bob"]',
            RuntimeError("LLM error"),
            "# Bob\nSidekick.",
            *["chunk response"] * 7,
            "Bob abridged",
            "Bob summary",
        ]
    )
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
        patch("presentation.orchestrator.StoryFoundationAgent") as foundation_cls,
        patch("presentation.orchestrator.OutlinePlannerAgent") as outline_cls,
        patch("presentation.orchestrator.StoryMetadataAgent") as metadata_cls,
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
        patch(
            "presentation.orchestrator._generate_setting_sheets",
            new=AsyncMock(return_value=[]),
        ),
    ):
        foundation_cls.return_value.run = AsyncMock(return_value=_outline_result())
        outline_cls.return_value.run = AsyncMock(return_value=_outline_result())
        metadata_cls.return_value.run = AsyncMock(return_value=_story_metadata_result())
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
    characters_dir = tmp_path / "test-story" / "characters"
    assert characters_dir.exists()
    assert (characters_dir / "bob.json").exists()
    assert not (characters_dir / "alice.json").exists()
    sheet_files = {
        p.name for p in characters_dir.glob("*.json") if p.name != "_names.json"
    }
    assert sheet_files == {"bob.json"}
    assert (characters_dir / "_names.json").exists()


@pytest.mark.asyncio
async def test_settings_phase_writes_sheets_to_disk(tmp_path: Path) -> None:
    """Settings phase writes setting sheet JSON files to disk."""
    provider = MagicMock()
    provider.generate_text = AsyncMock(
        side_effect=[
            '["The Citadel", "Dark Forest"]',
            "# The Citadel\nA fortified city.",
            *["chunk response"] * 6,
            "The Citadel abridged",
            "The Citadel summary",
            "# Dark Forest\nA mysterious woodland.",
            *["chunk response"] * 6,
            "Dark Forest abridged",
            "Dark Forest summary",
        ]
    )
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
        patch("presentation.orchestrator.StoryFoundationAgent") as foundation_cls,
        patch("presentation.orchestrator.OutlinePlannerAgent") as outline_cls,
        patch("presentation.orchestrator.StoryMetadataAgent") as metadata_cls,
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
        patch(
            "presentation.orchestrator._generate_character_sheets",
            new=AsyncMock(return_value=_generated_character_paths()),
        ),
    ):
        foundation_cls.return_value.run = AsyncMock(return_value=_outline_result())
        outline_cls.return_value.run = AsyncMock(return_value=_outline_result())
        metadata_cls.return_value.run = AsyncMock(return_value=_story_metadata_result())
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

    settings_dir = tmp_path / "test-story" / "settings"
    assert settings_dir.exists()
    written = [p for p in settings_dir.glob("*.json") if p.name != "_names.json"]
    assert len(written) == 2
    names_written = {
        json.loads(path.read_text(encoding="utf-8"))["name"] for path in written
    }
    assert names_written == {"The Citadel", "Dark Forest"}
    assert (settings_dir / "_names.json").exists()


@pytest.mark.asyncio
async def test_characters_phase_graceful_on_invalid_json(tmp_path: Path) -> None:
    """Malformed character names response leaves phase incomplete and raises."""
    provider = MagicMock()
    provider.generate_text = AsyncMock(return_value="not valid json at all")
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
        patch(
            "presentation.orchestrator._generate_setting_sheets",
            new=AsyncMock(return_value=[]),
        ),
    ):
        outline_cls.return_value.run = AsyncMock(return_value=_outline_result())
        chapter_cls.return_value.run = AsyncMock(return_value=_chapter_draft())
        wiki_cls.return_value.run = AsyncMock(return_value=_wiki_batch())
        consistency_cls.return_value.run = AsyncMock(
            return_value={"issues": [], "passed": True}
        )

        with pytest.raises(
            StoryGenerationError,
            match=r"\[Characters\] No character sheets were generated",
        ):
            await run_pipeline(
                "test-story",
                NullApprovalGate(),
                bus,
                wiki_bus,
                config=_config(),
                provider=provider,
            )

    characters_dir = tmp_path / "test-story" / "characters"
    if characters_dir.exists():
        assert len(list(characters_dir.glob("*.json"))) == 0


@pytest.mark.asyncio
async def test_narrative_arc_phase_runs_after_outline(tmp_path: Path) -> None:
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
        patch("presentation.orchestrator.StoryPlannerAgent") as arc_agent_cls,
        patch("presentation.orchestrator.OutlinePlannerAgent") as outline_cls,
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
        patch("presentation.orchestrator.FinalEditorAgent") as final_editor_cls,
        patch(
            "presentation.orchestrator._generate_character_sheets",
            new=AsyncMock(return_value=_generated_character_paths()),
        ),
        patch(
            "presentation.orchestrator._generate_setting_sheets",
            new=AsyncMock(return_value=[]),
        ),
    ):
        outline_cls.return_value.run = AsyncMock(return_value=_outline_result())
        arc_agent_cls.return_value.run = AsyncMock(
            return_value=ArcAnalysisResult(
                story_name="test-story",
                arc_assessment="Strong arc",
                verdict_code="strong",
                overall_score=0.9,
            )
        )
        chapter_cls.return_value.run = AsyncMock(return_value=_chapter_draft())
        wiki_cls.return_value.run = AsyncMock(return_value=_wiki_batch())
        consistency_cls.return_value.run = AsyncMock(
            return_value={"issues": [], "passed": True}
        )
        final_editor_cls.return_value.run = AsyncMock(
            return_value=FinalEditResult(
                story_name="test-story",
                chapters_processed=1,
                total_issues_found=0,
                total_revisions_made=0,
                edited_chapters=[_chapter_draft()],
            )
        )

        state = await run_pipeline(
            "test-story",
            NullApprovalGate(),
            bus,
            wiki_bus,
            config=_config(),
            provider=provider,
        )

    arc_agent_cls.return_value.run.assert_awaited_once()
    assert "narrative-arc" in state.completed_phases
    assert "arc_analysis_complete" in state.savepoints
    assert state.arc_result is not None
    assert state.arc_result.verdict_code == "strong"


@pytest.mark.asyncio
async def test_narrative_arc_phase_advisory_continues_on_error(tmp_path: Path) -> None:
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
        patch("presentation.orchestrator.StoryPlannerAgent") as arc_agent_cls,
        patch("presentation.orchestrator.OutlinePlannerAgent") as outline_cls,
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
        patch("presentation.orchestrator.FinalEditorAgent") as final_editor_cls,
        patch(
            "presentation.orchestrator._generate_character_sheets",
            new=AsyncMock(return_value=_generated_character_paths()),
        ),
        patch(
            "presentation.orchestrator._generate_setting_sheets",
            new=AsyncMock(return_value=[]),
        ),
    ):
        outline_cls.return_value.run = AsyncMock(return_value=_outline_result())
        arc_agent_cls.return_value.run = AsyncMock(
            side_effect=RuntimeError("arc failed")
        )
        chapter_cls.return_value.run = AsyncMock(return_value=_chapter_draft())
        wiki_cls.return_value.run = AsyncMock(return_value=_wiki_batch())
        consistency_cls.return_value.run = AsyncMock(
            return_value={"issues": [], "passed": True}
        )
        final_editor_cls.return_value.run = AsyncMock(
            return_value=FinalEditResult(
                story_name="test-story",
                chapters_processed=1,
                total_issues_found=0,
                total_revisions_made=0,
                edited_chapters=[_chapter_draft()],
            )
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
    assert "narrative-arc" in state.completed_phases


@pytest.mark.asyncio
async def test_final_edit_phase_invokes_agent(tmp_path: Path) -> None:
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
        patch("presentation.orchestrator.StoryPlannerAgent") as arc_agent_cls,
        patch("presentation.orchestrator.OutlinePlannerAgent") as outline_cls,
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
        patch("presentation.orchestrator.FinalEditorAgent") as final_editor_cls,
        patch(
            "presentation.orchestrator._generate_character_sheets",
            new=AsyncMock(return_value=_generated_character_paths()),
        ),
        patch(
            "presentation.orchestrator._generate_setting_sheets",
            new=AsyncMock(return_value=[]),
        ),
    ):
        outline_cls.return_value.run = AsyncMock(return_value=_outline_result())
        arc_agent_cls.return_value.run = AsyncMock(
            return_value=ArcAnalysisResult(
                story_name="test-story",
                arc_assessment="Strong arc",
                verdict_code="strong",
                overall_score=0.9,
            )
        )
        chapter_cls.return_value.run = AsyncMock(return_value=_chapter_draft())
        wiki_cls.return_value.run = AsyncMock(return_value=_wiki_batch())
        consistency_cls.return_value.run = AsyncMock(
            return_value={"issues": [], "passed": True}
        )
        final_editor_cls.return_value.build_prior_summaries.return_value = [""]
        final_editor_cls.return_value.edit_single_chapter = AsyncMock(
            return_value=ChapterDraft(
                story_name="test-story",
                chapter_number=1,
                title="Chapter 1",
                content="Edited content",
                word_count=2,
            )
        )

        state = await run_pipeline(
            "test-story",
            NullApprovalGate(),
            bus,
            wiki_bus,
            config=_config(),
            provider=provider,
        )

    final_editor_cls.return_value.edit_single_chapter.assert_awaited_once()
    assert "final-edit" in state.completed_phases
    assert "final_edit_complete" in state.savepoints
    edited_path = tmp_path / "test-story" / "output" / "story_edited.md"
    assert edited_path.exists()
    assert "Edited content" in edited_path.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_final_edit_exception_does_not_abort_assembly(tmp_path: Path) -> None:
    provider = MagicMock()
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    original_draft = ChapterDraft(
        story_name="test-story",
        chapter_number=1,
        title="Chapter 1",
        content="Original approved content",
        word_count=3,
    )

    def fake_savepoint_path(story_name: str) -> Path:
        return tmp_path / story_name / "savepoints" / "pipeline_state.json"

    with (
        patch(
            "presentation.orchestrator._savepoint_path", side_effect=fake_savepoint_path
        ),
        patch("presentation.orchestrator.STORIES_DIR", tmp_path),
        patch("tools._io.STORIES_DIR", tmp_path),
        patch("presentation.orchestrator.StoryPlannerAgent") as arc_agent_cls,
        patch("presentation.orchestrator.OutlinePlannerAgent") as outline_cls,
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
        patch("presentation.orchestrator.FinalEditorAgent") as final_editor_cls,
        patch(
            "presentation.orchestrator._generate_character_sheets",
            new=AsyncMock(return_value=_generated_character_paths()),
        ),
        patch(
            "presentation.orchestrator._generate_setting_sheets",
            new=AsyncMock(return_value=[]),
        ),
    ):
        outline_cls.return_value.run = AsyncMock(return_value=_outline_result())
        arc_agent_cls.return_value.run = AsyncMock(
            return_value=ArcAnalysisResult(
                story_name="test-story",
                arc_assessment="Strong arc",
                verdict_code="strong",
                overall_score=0.9,
            )
        )
        chapter_cls.return_value.run = AsyncMock(return_value=original_draft)
        wiki_cls.return_value.run = AsyncMock(return_value=_wiki_batch())
        consistency_cls.return_value.run = AsyncMock(
            return_value={"issues": [], "passed": True}
        )
        final_editor_cls.return_value.build_prior_summaries.return_value = [""]
        final_editor_cls.return_value.edit_single_chapter = AsyncMock(
            side_effect=RuntimeError("LLM timeout")
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
    final_editor_cls.return_value.edit_single_chapter.assert_awaited_once()
    output_path = tmp_path / "test-story" / "output" / "story.md"
    assert output_path.exists()
    assert output_path.read_text(encoding="utf-8") == "Original approved content\n"
    assert [chapter.content for chapter in state.approved_chapters] == [
        "Original approved content"
    ]
    assert not (tmp_path / "test-story" / "output" / "story_edited.md").exists()


@pytest.mark.asyncio
async def test_final_edit_phase_skipped_when_disabled(tmp_path: Path) -> None:
    provider = MagicMock()
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    config = _config()
    config["generation"] = {
        "wanted_chapters": 1,
        "seed": 12,
        "enable_final_edit": False,
    }

    def fake_savepoint_path(story_name: str) -> Path:
        return tmp_path / story_name / "savepoints" / "pipeline_state.json"

    with (
        patch(
            "presentation.orchestrator._savepoint_path", side_effect=fake_savepoint_path
        ),
        patch("presentation.orchestrator.STORIES_DIR", tmp_path),
        patch("tools._io.STORIES_DIR", tmp_path),
        patch("presentation.orchestrator.StoryPlannerAgent") as arc_agent_cls,
        patch("presentation.orchestrator.OutlinePlannerAgent") as outline_cls,
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
        patch("presentation.orchestrator.FinalEditorAgent") as final_editor_cls,
        patch(
            "presentation.orchestrator._generate_character_sheets",
            new=AsyncMock(return_value=_generated_character_paths()),
        ),
        patch(
            "presentation.orchestrator._generate_setting_sheets",
            new=AsyncMock(return_value=[]),
        ),
    ):
        outline_cls.return_value.run = AsyncMock(return_value=_outline_result())
        arc_agent_cls.return_value.run = AsyncMock(
            return_value=ArcAnalysisResult(
                story_name="test-story",
                arc_assessment="Strong arc",
                verdict_code="strong",
                overall_score=0.9,
            )
        )
        chapter_cls.return_value.run = AsyncMock(return_value=_chapter_draft())
        wiki_cls.return_value.run = AsyncMock(return_value=_wiki_batch())
        consistency_cls.return_value.run = AsyncMock(
            return_value={"issues": [], "passed": True}
        )
        final_editor_cls.return_value.run = AsyncMock(
            return_value=FinalEditResult(
                story_name="test-story",
                chapters_processed=1,
                total_issues_found=0,
                total_revisions_made=1,
                edited_chapters=[_chapter_draft()],
            )
        )

        state = await run_pipeline(
            "test-story",
            NullApprovalGate(),
            bus,
            wiki_bus,
            config=config,
            provider=provider,
        )

    final_editor_cls.return_value.run.assert_not_awaited()
    assert "final-edit" in state.completed_phases
    assert not (tmp_path / "test-story" / "output" / "story_edited.md").exists()


@pytest.mark.asyncio
async def test_wiki_initialised_before_chapter_loop(tmp_path: Path) -> None:
    provider = MagicMock()
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()

    def fake_savepoint_path(story_name: str) -> Path:
        return tmp_path / story_name / "savepoints" / "pipeline_state.json"

    (tmp_path / "test-story").mkdir(parents=True, exist_ok=True)

    with (
        patch(
            "presentation.orchestrator._savepoint_path", side_effect=fake_savepoint_path
        ),
        patch("presentation.orchestrator.STORIES_DIR", tmp_path),
        patch("tools._io.STORIES_DIR", tmp_path),
        patch("presentation.orchestrator.OutlinePlannerAgent") as outline_cls,
        patch("presentation.orchestrator.StoryPlannerAgent") as arc_agent_cls,
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
        patch(
            "presentation.orchestrator._generate_character_sheets",
            new=AsyncMock(return_value=_generated_character_paths()),
        ),
        patch(
            "presentation.orchestrator._generate_setting_sheets",
            new=AsyncMock(return_value=[]),
        ),
    ):
        outline_cls.return_value.run = AsyncMock(return_value=_outline_result())
        arc_agent_cls.return_value.run = AsyncMock(
            return_value=ArcAnalysisResult(
                story_name="test-story",
                arc_assessment="Strong arc",
                verdict_code="strong",
                overall_score=0.9,
            )
        )
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

    assert (tmp_path / "test-story" / "wiki" / "index.md").exists()
    assert (tmp_path / "test-story" / "wiki" / "log.md").exists()


@pytest.mark.asyncio
async def test_wiki_initialisation_idempotent_on_resume(tmp_path: Path) -> None:
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

    story_dir = tmp_path / "test-story"
    story_dir.mkdir(parents=True, exist_ok=True)
    wiki_dir = story_dir / "wiki"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    (wiki_dir / "index.md").write_text("# Pre-existing index\n", encoding="utf-8")

    with (
        patch(
            "presentation.orchestrator._savepoint_path", side_effect=fake_savepoint_path
        ),
        patch("presentation.orchestrator.STORIES_DIR", tmp_path),
        patch("tools._io.STORIES_DIR", tmp_path),
        patch("presentation.orchestrator.StoryPlannerAgent") as arc_agent_cls,
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
        patch(
            "presentation.orchestrator._generate_character_sheets",
            new=AsyncMock(return_value=_generated_character_paths()),
        ),
        patch(
            "presentation.orchestrator._generate_setting_sheets",
            new=AsyncMock(return_value=[]),
        ),
    ):
        arc_agent_cls.return_value.run = AsyncMock(
            return_value=ArcAnalysisResult(
                story_name="test-story",
                arc_assessment="Strong arc",
                verdict_code="strong",
                overall_score=0.9,
            )
        )
        chapter_cls.return_value.run = AsyncMock(return_value=_chapter_draft())
        wiki_cls.return_value.run = AsyncMock(return_value=_wiki_batch())
        consistency_cls.return_value.run = AsyncMock(
            return_value={"issues": [], "passed": True}
        )

        await _write_savepoint(partial_state)

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
    assert (wiki_dir / "index.md").read_text(
        encoding="utf-8"
    ) == "# Pre-existing index\n"


@pytest.mark.asyncio
async def test_wiki_init_error_raises_story_generation_error(
    tmp_path: Path,
) -> None:
    provider = MagicMock()
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()

    def fake_savepoint_path(story_name: str) -> Path:
        return tmp_path / story_name / "savepoints" / "pipeline_state.json"

    (tmp_path / "test-story").mkdir(parents=True, exist_ok=True)

    with (
        patch(
            "presentation.orchestrator._savepoint_path", side_effect=fake_savepoint_path
        ),
        patch("presentation.orchestrator.STORIES_DIR", tmp_path),
        patch("tools._io.STORIES_DIR", tmp_path),
        patch(
            "presentation.orchestrator._init_wiki_for_story",
            return_value={
                "error": "story directory not found",
                "story_name": "test-story",
            },
        ),
        patch("presentation.orchestrator.OutlinePlannerAgent") as outline_cls,
        patch("presentation.orchestrator.StoryPlannerAgent") as arc_agent_cls,
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
        patch(
            "presentation.orchestrator._generate_character_sheets",
            new=AsyncMock(return_value=_generated_character_paths()),
        ),
        patch(
            "presentation.orchestrator._generate_setting_sheets",
            new=AsyncMock(return_value=[]),
        ),
    ):
        outline_cls.return_value.run = AsyncMock(return_value=_outline_result())
        arc_agent_cls.return_value.run = AsyncMock(
            return_value=ArcAnalysisResult(
                story_name="test-story",
                arc_assessment="Strong arc",
                verdict_code="strong",
                overall_score=0.9,
            )
        )
        chapter_cls.return_value.run = AsyncMock(return_value=_chapter_draft())
        wiki_cls.return_value.run = AsyncMock(return_value=_wiki_batch())
        consistency_cls.return_value.run = AsyncMock(
            return_value={"issues": [], "passed": True}
        )

        with pytest.raises(
            StoryGenerationError,
            match="Wiki initialization failed for story 'test-story': story directory not found",
        ):
            await run_pipeline(
                "test-story",
                NullApprovalGate(),
                bus,
                wiki_bus,
                config=_config(),
                provider=provider,
            )


@pytest.mark.asyncio
async def test_consistency_warnings_emitted_even_when_passed_true(
    tmp_path: Path,
) -> None:
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
        patch(
            "presentation.orchestrator._generate_character_sheets",
            new=AsyncMock(return_value=_generated_character_paths()),
        ),
        patch(
            "presentation.orchestrator._generate_setting_sheets",
            new=AsyncMock(return_value=[]),
        ),
    ):
        outline_cls.return_value.run = AsyncMock(return_value=_outline_result())
        chapter_cls.return_value.run = AsyncMock(return_value=_chapter_draft())
        wiki_cls.return_value.run = AsyncMock(return_value=_wiki_batch())
        consistency_cls.return_value.run = AsyncMock(
            return_value={
                "issues": [
                    {
                        "type": "semantic",
                        "description": "Minor name inconsistency",
                        "severity": "warning",
                    }
                ],
                "passed": True,
            }
        )

        state = await run_pipeline(
            "test-story",
            NullApprovalGate(),
            bus,
            wiki_bus,
            config=_config(),
            provider=provider,
        )

    tokens: list[str] = []
    async for token in bus:
        tokens.append(token)
    emitted = "".join(tokens)

    assert state.status == "complete"
    assert "[Consistency] Chapter 1 — warnings/info found:" in emitted
    assert "[WARNING] Minor name inconsistency" in emitted


def test_work_item_done_returns_false_when_not_present() -> None:
    """_work_item_done returns False when item not in completed_work_items."""
    state = PipelineState(story_name="test", current_phase="characters")

    result = _work_item_done(state, "characters", "characters/alice/sheet")

    assert result is False


def test_work_item_done_returns_true_when_present() -> None:
    """_work_item_done returns True when item is in completed_work_items."""
    state = PipelineState(
        story_name="test",
        current_phase="characters",
        completed_work_items={"characters": ["characters/alice/sheet"]},
    )

    result = _work_item_done(state, "characters", "characters/alice/sheet")

    assert result is True


def test_work_item_done_different_phase_returns_false() -> None:
    """_work_item_done returns False when item is in a different phase."""
    state = PipelineState(
        story_name="test",
        current_phase="characters",
        completed_work_items={"settings": ["characters/alice/sheet"]},
    )

    result = _work_item_done(state, "characters", "characters/alice/sheet")

    assert result is False


@pytest.mark.asyncio
async def test_mark_work_item_done_appends_and_saves(tmp_path: Path) -> None:
    """_mark_work_item_done appends item_id to ledger and writes savepoint."""
    state = PipelineState(story_name="test-story", current_phase="characters")

    def fake_savepoint_path(story_name: str) -> Path:
        return tmp_path / story_name / "savepoints" / "pipeline_state.json"

    with patch(
        "presentation.orchestrator._savepoint_path", side_effect=fake_savepoint_path
    ):
        await _mark_work_item_done(state, "characters", "characters/alice/sheet")

    assert "characters/alice/sheet" in state.completed_work_items["characters"]
    saved_path = fake_savepoint_path("test-story")
    assert saved_path.exists()
    saved = json.loads(saved_path.read_text())
    assert "characters/alice/sheet" in saved["completed_work_items"]["characters"]


@pytest.mark.asyncio
async def test_mark_work_item_done_idempotent(tmp_path: Path) -> None:
    """_mark_work_item_done does not duplicate items when called twice."""
    state = PipelineState(story_name="test-story", current_phase="characters")

    def fake_savepoint_path(story_name: str) -> Path:
        return tmp_path / story_name / "savepoints" / "pipeline_state.json"

    with patch(
        "presentation.orchestrator._savepoint_path", side_effect=fake_savepoint_path
    ):
        await _mark_work_item_done(state, "characters", "characters/alice/sheet")
        await _mark_work_item_done(state, "characters", "characters/alice/sheet")

    assert state.completed_work_items["characters"].count("characters/alice/sheet") == 1


@pytest.mark.asyncio
async def test_write_savepoint_atomic_leaves_prior_intact_on_failure(
    tmp_path: Path,
) -> None:
    """_write_savepoint is atomic: if os.replace fails, prior savepoint is not corrupted."""
    state = PipelineState(story_name="test-story", current_phase="outline")

    def fake_savepoint_path(story_name: str) -> Path:
        return tmp_path / story_name / "savepoints" / "pipeline_state.json"

    with patch(
        "presentation.orchestrator._savepoint_path", side_effect=fake_savepoint_path
    ):
        await _write_savepoint(state)

    initial_path = fake_savepoint_path("test-story")
    original_content = initial_path.read_text()

    def failing_replace(src: str, dst: str) -> None:
        raise OSError("Simulated mid-write failure")

    state2 = PipelineState(story_name="test-story", current_phase="characters")
    with (
        patch(
            "presentation.orchestrator._savepoint_path",
            side_effect=fake_savepoint_path,
        ),
        patch("os.replace", side_effect=failing_replace),
    ):
        with pytest.raises(OSError):
            await _write_savepoint(state2)

    assert initial_path.read_text() == original_content


@pytest.mark.asyncio
async def test_characters_phase_resumes_from_names_cache(tmp_path: Path) -> None:
    provider = MagicMock()
    provider.generate_text = AsyncMock(
        side_effect=[
            "# Alice\nHero of the story.",
            *["chunk response"] * 7,
            "Alice abridged",
            "Alice summary",
            "# Bob\nSidekick.",
            *["chunk response"] * 7,
            "Bob abridged",
            "Bob summary",
        ]
    )
    state = PipelineState(
        story_name="test-story",
        current_phase="characters",
        completed_work_items={"characters": ["_extract_names"]},
    )
    characters_dir = tmp_path / "test-story" / "characters"
    characters_dir.mkdir(parents=True, exist_ok=True)
    (characters_dir / "_names.json").write_text(
        json.dumps(["Alice", "Bob"]), encoding="utf-8"
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
        written = await _generate_character_sheets(
            "test-story",
            state,
            _outline_result(),
            provider,
            _config(),
            tmp_path,
        )

    assert len(written) == 2
    assert provider.generate_text.await_count == 20
    assert (characters_dir / "alice.json").exists()
    assert (characters_dir / "bob.json").exists()


@pytest.mark.asyncio
async def test_characters_phase_resumes_skipping_completed_sheet(
    tmp_path: Path,
) -> None:
    provider = MagicMock()
    provider.generate_text = AsyncMock(
        side_effect=[
            "# Bob\nSidekick.",
            *["chunk"] * 7,
            "Bob abridged",
            "Bob summary",
        ]
    )
    state = PipelineState(
        story_name="test-story",
        current_phase="characters",
        completed_work_items={
            "characters": [
                "_extract_names",
                "characters/alice/sheet",
                "characters/alice/chunk:backstory",
                "characters/alice/chunk:personality",
                "characters/alice/chunk:motivation",
                "characters/alice/chunk:relationships",
                "characters/alice/chunk:skills",
                "characters/alice/chunk:arc",
                "characters/alice/chunk:current_state",
                "characters/alice/abridged",
                "characters/alice/summary",
            ]
        },
    )
    characters_dir = tmp_path / "test-story" / "characters"
    characters_dir.mkdir(parents=True, exist_ok=True)
    (characters_dir / "_names.json").write_text(
        json.dumps(["Alice", "Bob"]), encoding="utf-8"
    )
    (characters_dir / "alice.json").write_text(
        json.dumps(
            {
                "name": "Alice",
                "sheet": "existing sheet text",
                "chunks": {
                    "backstory": "bg",
                    "personality": "p",
                    "motivation": "m",
                    "relationships": "r",
                    "skills": "s",
                    "arc": "a",
                    "current_state": "cs",
                },
                "abridged": "alice abridged",
                "summary": "alice summary",
                "updated_at": "2026-05-03T00:00:00+00:00",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
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
        written = await _generate_character_sheets(
            "test-story",
            state,
            _outline_result(),
            provider,
            _config(),
            tmp_path,
        )

    assert {path.name for path in written} == {"alice.json", "bob.json"}
    assert provider.generate_text.await_count == 10


@pytest.mark.asyncio
async def test_settings_phase_resumes_from_locations_cache(tmp_path: Path) -> None:
    provider = MagicMock()
    provider.generate_text = AsyncMock(
        side_effect=[
            "# The Citadel\nDesc.",
            *["chunk"] * 6,
            "abridged",
            "summary",
        ]
    )
    state = PipelineState(
        story_name="test-story",
        current_phase="settings",
        completed_work_items={"settings": ["_extract_locations"]},
    )
    settings_dir = tmp_path / "test-story" / "settings"
    settings_dir.mkdir(parents=True, exist_ok=True)
    (settings_dir / "_names.json").write_text(
        json.dumps(["The Citadel"]), encoding="utf-8"
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
        written = await _generate_setting_sheets(
            "test-story",
            state,
            _outline_result(),
            provider,
            _config(),
            tmp_path,
        )

    assert len(written) == 1
    assert provider.generate_text.await_count == 9
    assert (settings_dir / "the-citadel.json").exists()


@pytest.mark.asyncio
async def test_chapter_loop_resumes_at_consistency_check(tmp_path: Path) -> None:
    provider = MagicMock()
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()

    partial_state = PipelineState(
        story_name="test-story",
        current_phase="chapter-1",
        completed_phases=[
            "init",
            "story-foundation",
            "outline",
            "metadata-outline",
            "narrative-arc",
            "characters",
            "settings",
            "wiki-bootstrap",
        ],
        outline_result=_outline_result(),
        approved_chapters=[_chapter_draft()],
        completed_work_items={"chapter-1": ["chapter-1/draft"]},
        savepoints=[
            "init",
            "story_foundation_complete",
            "outline",
            "metadata_outline_complete",
            "arc_analysis_complete",
            "characters",
            "settings",
            "wiki_populated",
        ],
        status="running",
    )

    def fake_savepoint_path(story_name: str) -> Path:
        return tmp_path / story_name / "savepoints" / "pipeline_state.json"

    story_dir = tmp_path / "test-story"
    story_dir.mkdir(parents=True, exist_ok=True)

    with (
        patch(
            "presentation.orchestrator._savepoint_path", side_effect=fake_savepoint_path
        ),
        patch("presentation.orchestrator.STORIES_DIR", tmp_path),
        patch("tools._io.STORIES_DIR", tmp_path),
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.StoryMetadataAgent") as metadata_cls,
        patch("presentation.orchestrator.FinalEditorAgent") as final_editor_cls,
        patch("presentation.agents.recap_writer.RecapWriterAgent") as recap_cls,
    ):
        chapter_cls.return_value.run = AsyncMock(return_value=_chapter_draft())
        consistency_cls.return_value.run = AsyncMock(
            return_value={"issues": [], "passed": True}
        )
        wiki_cls.return_value.run = AsyncMock(return_value=_wiki_batch())
        recap_cls.return_value.run = AsyncMock(return_value={"events": []})
        metadata_cls.return_value.run = AsyncMock(return_value=_story_metadata_result())
        final_editor_cls.return_value.build_prior_summaries = MagicMock(
            return_value=[""]
        )
        final_editor_cls.return_value.edit_single_chapter = AsyncMock(
            return_value=_chapter_draft()
        )

        await _write_savepoint(partial_state)

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
    chapter_cls.return_value.run.assert_not_awaited()
    consistency_cls.return_value.run.assert_awaited_once()


def _resume_state(
    *,
    current_phase: str,
    outline_result: OutlineResult | None = None,
    approved_chapters: list[ChapterDraft] | None = None,
    completed_phases: list[str] | None = None,
    completed_work_items: dict[str, list[str]] | None = None,
) -> PipelineState:
    return PipelineState(
        story_name="test-story",
        current_phase=current_phase,
        completed_phases=completed_phases
        or [
            "init",
            "story-foundation",
            "outline",
            "metadata-outline",
            "narrative-arc",
            "characters",
            "settings",
            "wiki-bootstrap",
        ],
        outline_result=outline_result or _outline_result(),
        approved_chapters=approved_chapters or [_chapter_draft()],
        completed_work_items=completed_work_items or {},
        savepoints=[
            "init",
            "story_foundation_complete",
            "outline",
            "metadata_outline_complete",
            "arc_analysis_complete",
            "characters",
            "settings",
            "wiki_populated",
        ],
        status="running",
    )


@pytest.mark.asyncio
async def test_chapter_loop_resumes_at_wiki_update(tmp_path: Path) -> None:
    provider = MagicMock()
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    state = _resume_state(
        current_phase="chapter-1",
        completed_work_items={
            "chapter-1": [
                "chapter-1/draft",
                "chapter-1/consistency-check",
            ]
        },
    )

    def fake_savepoint_path(story_name: str) -> Path:
        return tmp_path / story_name / "savepoints" / "pipeline_state.json"

    (tmp_path / "test-story").mkdir(parents=True, exist_ok=True)

    with (
        patch(
            "presentation.orchestrator._savepoint_path", side_effect=fake_savepoint_path
        ),
        patch("presentation.orchestrator.STORIES_DIR", tmp_path),
        patch("tools._io.STORIES_DIR", tmp_path),
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.StoryMetadataAgent") as metadata_cls,
        patch("presentation.orchestrator.FinalEditorAgent") as final_editor_cls,
        patch("presentation.agents.recap_writer.RecapWriterAgent") as recap_cls,
    ):
        chapter_cls.return_value.run = AsyncMock(return_value=_chapter_draft())
        consistency_cls.return_value.run = AsyncMock(
            return_value={"issues": [], "passed": True}
        )
        wiki_cls.return_value.run = AsyncMock(return_value=_wiki_batch())
        recap_cls.return_value.run = AsyncMock(return_value={"events": []})
        metadata_cls.return_value.run = AsyncMock(return_value=_story_metadata_result())
        final_editor_cls.return_value.build_prior_summaries = MagicMock(
            return_value=[""]
        )
        final_editor_cls.return_value.edit_single_chapter = AsyncMock(
            return_value=_chapter_draft()
        )

        await _write_savepoint(state)

        await resume_pipeline(
            "test-story",
            None,
            NullApprovalGate(),
            bus,
            wiki_bus,
            config=_config(),
            provider=provider,
        )

    chapter_cls.return_value.run.assert_not_awaited()
    consistency_cls.return_value.run.assert_not_awaited()
    wiki_cls.return_value.run.assert_awaited_once()


@pytest.mark.asyncio
async def test_chapter_loop_resumes_at_recap_after_wiki_update(tmp_path: Path) -> None:
    provider = MagicMock()
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    state = _resume_state(
        current_phase="chapter-1",
        completed_work_items={
            "chapter-1": [
                "chapter-1/draft",
                "chapter-1/consistency-check",
                "chapter-1/wiki-update",
            ]
        },
    )

    def fake_savepoint_path(story_name: str) -> Path:
        return tmp_path / story_name / "savepoints" / "pipeline_state.json"

    (tmp_path / "test-story").mkdir(parents=True, exist_ok=True)

    with (
        patch(
            "presentation.orchestrator._savepoint_path", side_effect=fake_savepoint_path
        ),
        patch("presentation.orchestrator.STORIES_DIR", tmp_path),
        patch("tools._io.STORIES_DIR", tmp_path),
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.StoryMetadataAgent") as metadata_cls,
        patch("presentation.orchestrator.FinalEditorAgent") as final_editor_cls,
        patch("presentation.agents.recap_writer.RecapWriterAgent") as recap_cls,
    ):
        chapter_cls.return_value.run = AsyncMock(return_value=_chapter_draft())
        consistency_cls.return_value.run = AsyncMock(
            return_value={"issues": [], "passed": True}
        )
        wiki_cls.return_value.run = AsyncMock(return_value=_wiki_batch())
        recap_cls.return_value.run = AsyncMock(return_value={"events": []})
        metadata_cls.return_value.run = AsyncMock(return_value=_story_metadata_result())
        final_editor_cls.return_value.build_prior_summaries = MagicMock(
            return_value=[""]
        )
        final_editor_cls.return_value.edit_single_chapter = AsyncMock(
            return_value=_chapter_draft()
        )

        await _write_savepoint(state)

        await resume_pipeline(
            "test-story",
            None,
            NullApprovalGate(),
            bus,
            wiki_bus,
            config=_config(),
            provider=provider,
        )

    wiki_cls.return_value.run.assert_not_awaited()
    recap_cls.return_value.run.assert_awaited_once()


@pytest.mark.asyncio
async def test_chapter_loop_resumes_at_recap(tmp_path: Path) -> None:
    provider = MagicMock()
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    state = _resume_state(
        current_phase="chapter-1",
        completed_work_items={
            "chapter-1": [
                "chapter-1/draft",
                "chapter-1/consistency-check",
                "chapter-1/wiki-update",
            ]
        },
    )

    def fake_savepoint_path(story_name: str) -> Path:
        return tmp_path / story_name / "savepoints" / "pipeline_state.json"

    (tmp_path / "test-story").mkdir(parents=True, exist_ok=True)

    with (
        patch(
            "presentation.orchestrator._savepoint_path", side_effect=fake_savepoint_path
        ),
        patch("presentation.orchestrator.STORIES_DIR", tmp_path),
        patch("tools._io.STORIES_DIR", tmp_path),
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.StoryMetadataAgent") as metadata_cls,
        patch("presentation.orchestrator.FinalEditorAgent") as final_editor_cls,
        patch("presentation.agents.recap_writer.RecapWriterAgent") as recap_cls,
    ):
        chapter_cls.return_value.run = AsyncMock(return_value=_chapter_draft())
        consistency_cls.return_value.run = AsyncMock(
            return_value={"issues": [], "passed": True}
        )
        wiki_cls.return_value.run = AsyncMock(return_value=_wiki_batch())
        recap_cls.return_value.run = AsyncMock(return_value={"events": ["event"]})
        metadata_cls.return_value.run = AsyncMock(return_value=_story_metadata_result())
        final_editor_cls.return_value.build_prior_summaries = MagicMock(
            return_value=[""]
        )
        final_editor_cls.return_value.edit_single_chapter = AsyncMock(
            return_value=_chapter_draft()
        )

        await _write_savepoint(state)

        await resume_pipeline(
            "test-story",
            None,
            NullApprovalGate(),
            bus,
            wiki_bus,
            config=_config(),
            provider=provider,
        )

    wiki_cls.return_value.run.assert_not_awaited()
    recap_cls.return_value.run.assert_awaited_once()


@pytest.mark.asyncio
async def test_recap_persisted_when_events_empty(tmp_path: Path) -> None:
    provider = MagicMock()
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    state = _resume_state(
        current_phase="chapter-1",
        completed_work_items={
            "chapter-1": [
                "chapter-1/draft",
                "chapter-1/consistency-check",
                "chapter-1/wiki-update",
            ]
        },
    )

    def fake_savepoint_path(story_name: str) -> Path:
        return tmp_path / story_name / "savepoints" / "pipeline_state.json"

    story_dir = tmp_path / "test-story"
    story_dir.mkdir(parents=True, exist_ok=True)

    with (
        patch(
            "presentation.orchestrator._savepoint_path", side_effect=fake_savepoint_path
        ),
        patch("presentation.orchestrator.STORIES_DIR", tmp_path),
        patch("tools._io.STORIES_DIR", tmp_path),
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.StoryMetadataAgent") as metadata_cls,
        patch("presentation.orchestrator.FinalEditorAgent") as final_editor_cls,
        patch("presentation.agents.recap_writer.RecapWriterAgent") as recap_cls,
    ):
        chapter_cls.return_value.run = AsyncMock(return_value=_chapter_draft())
        consistency_cls.return_value.run = AsyncMock(
            return_value={"issues": [], "passed": True}
        )
        wiki_cls.return_value.run = AsyncMock(return_value=_wiki_batch())
        recap_cls.return_value.run = AsyncMock(
            return_value={
                "compact": "Compact summary",
                "sanitised": "Sanitised summary",
                "events": [],
            }
        )
        metadata_cls.return_value.run = AsyncMock(return_value=_story_metadata_result())
        final_editor_cls.return_value.build_prior_summaries = MagicMock(
            return_value=[""]
        )
        final_editor_cls.return_value.edit_single_chapter = AsyncMock(
            return_value=_chapter_draft()
        )

        await _write_savepoint(state)

        resumed = await resume_pipeline(
            "test-story",
            None,
            NullApprovalGate(),
            bus,
            wiki_bus,
            config=_config(),
            provider=provider,
        )

    recap_entry = resumed.recaps["1"]
    compact_ref = recap_entry["compact"]["$ref"]
    sanitised_ref = recap_entry["sanitised"]["$ref"]

    assert (story_dir / compact_ref).read_text(encoding="utf-8") == "Compact summary"
    assert (story_dir / sanitised_ref).read_text(
        encoding="utf-8"
    ) == "Sanitised summary"
    recap_cls.return_value.run.assert_awaited_once()


@pytest.mark.asyncio
async def test_chapter_loop_metadata_skipped_for_chapter_2(tmp_path: Path) -> None:
    provider = MagicMock()
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    chapter_1 = _chapter_draft()
    chapter_2 = ChapterDraft(
        story_name="test-story",
        chapter_number=2,
        title="Chapter 2",
        content="Second chapter draft",
        word_count=3,
    )
    state = _resume_state(
        current_phase="chapter-2",
        outline_result=_two_chapter_outline_result(),
        approved_chapters=[chapter_1, chapter_2],
        completed_phases=[
            "init",
            "story-foundation",
            "outline",
            "metadata-outline",
            "narrative-arc",
            "characters",
            "settings",
            "wiki-bootstrap",
            "chapter-1",
        ],
        completed_work_items={
            "chapter-2": [
                "chapter-2/draft",
                "chapter-2/consistency-check",
                "chapter-2/wiki-update",
            ]
        },
    )

    def fake_savepoint_path(story_name: str) -> Path:
        return tmp_path / story_name / "savepoints" / "pipeline_state.json"

    (tmp_path / "test-story").mkdir(parents=True, exist_ok=True)

    with (
        patch(
            "presentation.orchestrator._savepoint_path", side_effect=fake_savepoint_path
        ),
        patch("presentation.orchestrator.STORIES_DIR", tmp_path),
        patch("tools._io.STORIES_DIR", tmp_path),
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.StoryMetadataAgent") as metadata_cls,
        patch("presentation.orchestrator.FinalEditorAgent") as final_editor_cls,
        patch("presentation.agents.recap_writer.RecapWriterAgent") as recap_cls,
    ):
        chapter_cls.return_value.run = AsyncMock(return_value=chapter_2)
        consistency_cls.return_value.run = AsyncMock(
            return_value={"issues": [], "passed": True}
        )
        wiki_cls.return_value.run = AsyncMock(return_value=_wiki_batch())
        recap_cls.return_value.run = AsyncMock(return_value={"events": ["event"]})
        metadata_cls.return_value.run = AsyncMock(return_value=_story_metadata_result())
        final_editor_cls.return_value.build_prior_summaries = MagicMock(
            return_value=["", "Chapter 1 summary"]
        )
        final_editor_cls.return_value.edit_single_chapter = AsyncMock(
            side_effect=[chapter_1, chapter_2]
        )

        await _write_savepoint(state)

        resumed = await resume_pipeline(
            "test-story",
            None,
            NullApprovalGate(),
            bus,
            wiki_bus,
            config=_config(),
            provider=provider,
        )

    assert "chapter-2/metadata" not in resumed.completed_work_items.get("chapter-2", [])
    metadata_cls.return_value.run.assert_awaited_once()


@pytest.mark.asyncio
async def test_chapter_loop_backfills_draft_for_legacy_approved_chapter(
    tmp_path: Path,
) -> None:
    provider = MagicMock()
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    state = _resume_state(current_phase="chapter-1")

    def fake_savepoint_path(story_name: str) -> Path:
        return tmp_path / story_name / "savepoints" / "pipeline_state.json"

    (tmp_path / "test-story").mkdir(parents=True, exist_ok=True)

    with (
        patch(
            "presentation.orchestrator._savepoint_path", side_effect=fake_savepoint_path
        ),
        patch("presentation.orchestrator.STORIES_DIR", tmp_path),
        patch("tools._io.STORIES_DIR", tmp_path),
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.StoryMetadataAgent") as metadata_cls,
        patch("presentation.orchestrator.FinalEditorAgent") as final_editor_cls,
        patch("presentation.agents.recap_writer.RecapWriterAgent") as recap_cls,
    ):
        chapter_cls.return_value.run = AsyncMock(return_value=_chapter_draft())
        consistency_cls.return_value.run = AsyncMock(
            return_value={"issues": [], "passed": True}
        )
        wiki_cls.return_value.run = AsyncMock(return_value=_wiki_batch())
        recap_cls.return_value.run = AsyncMock(return_value={"events": []})
        metadata_cls.return_value.run = AsyncMock(return_value=_story_metadata_result())
        final_editor_cls.return_value.build_prior_summaries = MagicMock(
            return_value=[""]
        )
        final_editor_cls.return_value.edit_single_chapter = AsyncMock(
            return_value=_chapter_draft()
        )

        await _write_savepoint(state)

        resumed = await resume_pipeline(
            "test-story",
            None,
            NullApprovalGate(),
            bus,
            wiki_bus,
            config=_config(),
            provider=provider,
        )

    chapter_cls.return_value.run.assert_not_awaited()
    assert "chapter-1/draft" in resumed.completed_work_items["chapter-1"]


@pytest.mark.asyncio
async def test_final_edit_resumes_at_chapter_2(tmp_path: Path) -> None:
    provider = MagicMock()
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    chapter_1 = _chapter_draft()
    chapter_2 = ChapterDraft(
        story_name="test-story",
        chapter_number=2,
        title="Chapter 2",
        content="Draft chapter 2",
        word_count=3,
    )
    state = _resume_state(
        current_phase="final-edit",
        outline_result=_two_chapter_outline_result(),
        approved_chapters=[chapter_1, chapter_2],
        completed_phases=[
            "init",
            "story-foundation",
            "outline",
            "metadata-outline",
            "narrative-arc",
            "characters",
            "settings",
            "wiki-bootstrap",
            "chapter-1",
            "metadata-chapter-1",
            "chapter-2",
            "chapter-loop",
        ],
        completed_work_items={"final-edit": ["final-edit/chapter:1"]},
    )

    def fake_savepoint_path(story_name: str) -> Path:
        return tmp_path / story_name / "savepoints" / "pipeline_state.json"

    story_dir = tmp_path / "test-story"
    chapters_dir = story_dir / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)
    (chapters_dir / "chapter_1_edited.md").write_text(
        "Edited chapter 1 from disk", encoding="utf-8"
    )

    edited_chapter_2 = ChapterDraft(
        story_name="test-story",
        chapter_number=2,
        title="Chapter 2",
        content="Edited chapter 2",
        word_count=3,
    )

    with (
        patch(
            "presentation.orchestrator._savepoint_path", side_effect=fake_savepoint_path
        ),
        patch("presentation.orchestrator.STORIES_DIR", tmp_path),
        patch("tools._io.STORIES_DIR", tmp_path),
        patch("presentation.orchestrator.StoryMetadataAgent") as metadata_cls,
        patch("presentation.orchestrator.FinalEditorAgent") as final_editor_cls,
    ):
        metadata_cls.return_value.run = AsyncMock(return_value=_story_metadata_result())
        final_editor_cls.return_value.build_prior_summaries = MagicMock(
            return_value=["", "Chapter 1: prior"]
        )
        final_editor_cls.return_value.edit_single_chapter = AsyncMock(
            return_value=edited_chapter_2
        )

        await _write_savepoint(state)

        resumed = await resume_pipeline(
            "test-story",
            None,
            NullApprovalGate(),
            bus,
            wiki_bus,
            config=_config(),
            provider=provider,
        )

    final_editor_cls.return_value.edit_single_chapter.assert_awaited_once()
    assert resumed.approved_chapters[0].content == "Edited chapter 1 from disk"
    assert resumed.approved_chapters[1].content == "Edited chapter 2"


@pytest.mark.asyncio
async def test_outline_draft_skipped_on_resume(tmp_path: Path) -> None:
    provider = MagicMock()
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    config = _config()
    config["generation"] = {
        "wanted_chapters": 1,
        "seed": 12,
        "enable_outline_critique": False,
    }
    state = PipelineState(
        story_name="test-story",
        current_phase="outline",
        completed_phases=["init", "story-foundation"],
        outline_result=_outline_result(),
        completed_work_items={"outline": ["outline/draft"]},
        savepoints=["init", "story_foundation_complete"],
        status="running",
    )

    def fake_savepoint_path(story_name: str) -> Path:
        return tmp_path / story_name / "savepoints" / "pipeline_state.json"

    (tmp_path / "test-story").mkdir(parents=True, exist_ok=True)

    with (
        patch(
            "presentation.orchestrator._savepoint_path", side_effect=fake_savepoint_path
        ),
        patch("presentation.orchestrator.STORIES_DIR", tmp_path),
        patch("tools._io.STORIES_DIR", tmp_path),
        patch("presentation.orchestrator.OutlinePlannerAgent") as outline_cls,
        patch("presentation.orchestrator.StoryPlannerAgent") as arc_agent_cls,
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
        patch(
            "presentation.orchestrator._generate_character_sheets",
            new=AsyncMock(return_value=_generated_character_paths()),
        ),
        patch(
            "presentation.orchestrator._generate_setting_sheets",
            new=AsyncMock(return_value=[]),
        ),
    ):
        outline_cls.return_value.run = AsyncMock(return_value=_outline_result())
        arc_agent_cls.return_value.run = AsyncMock(
            return_value=ArcAnalysisResult(
                story_name="test-story",
                arc_assessment="Strong arc",
                verdict_code="strong",
                overall_score=0.9,
            )
        )
        chapter_cls.return_value.run = AsyncMock(return_value=_chapter_draft())
        wiki_cls.return_value.run = AsyncMock(return_value=_wiki_batch())
        consistency_cls.return_value.run = AsyncMock(
            return_value={"issues": [], "passed": True}
        )

        await _write_savepoint(state)

        await resume_pipeline(
            "test-story",
            None,
            NullApprovalGate(),
            bus,
            wiki_bus,
            config=config,
            provider=provider,
        )

    outline_cls.return_value.run.assert_not_awaited()


@pytest.mark.asyncio
async def test_outline_critique_skipped_on_resume(tmp_path: Path) -> None:
    provider = MagicMock()
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    config = _config()
    config["generation"] = {
        "wanted_chapters": 1,
        "seed": 12,
        "enable_outline_critique": True,
    }
    state = PipelineState(
        story_name="test-story",
        current_phase="outline",
        completed_phases=["init", "story-foundation"],
        outline_result=_outline_result(),
        completed_work_items={
            "outline": [
                "outline/draft",
                "outline/critique",
            ]
        },
        savepoints=["init", "story_foundation_complete"],
        status="running",
    )

    def fake_savepoint_path(story_name: str) -> Path:
        return tmp_path / story_name / "savepoints" / "pipeline_state.json"

    (tmp_path / "test-story").mkdir(parents=True, exist_ok=True)

    with (
        patch(
            "presentation.orchestrator._savepoint_path", side_effect=fake_savepoint_path
        ),
        patch("presentation.orchestrator.STORIES_DIR", tmp_path),
        patch("tools._io.STORIES_DIR", tmp_path),
        patch("presentation.orchestrator.OutlinePlannerAgent") as outline_cls,
        patch("presentation.orchestrator.OutlineCriticAgent") as critic_cls,
        patch("presentation.orchestrator.StoryPlannerAgent") as arc_agent_cls,
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
        patch(
            "presentation.orchestrator._generate_character_sheets",
            new=AsyncMock(return_value=_generated_character_paths()),
        ),
        patch(
            "presentation.orchestrator._generate_setting_sheets",
            new=AsyncMock(return_value=[]),
        ),
    ):
        outline_cls.return_value.run = AsyncMock(return_value=_outline_result())
        critic_cls.return_value.run = AsyncMock(return_value=state)
        arc_agent_cls.return_value.run = AsyncMock(
            return_value=ArcAnalysisResult(
                story_name="test-story",
                arc_assessment="Strong arc",
                verdict_code="strong",
                overall_score=0.9,
            )
        )
        chapter_cls.return_value.run = AsyncMock(return_value=_chapter_draft())
        wiki_cls.return_value.run = AsyncMock(return_value=_wiki_batch())
        consistency_cls.return_value.run = AsyncMock(
            return_value={"issues": [], "passed": True}
        )

        await _write_savepoint(state)

        await resume_pipeline(
            "test-story",
            None,
            NullApprovalGate(),
            bus,
            wiki_bus,
            config=config,
            provider=provider,
        )

    critic_cls.return_value.run.assert_not_awaited()


@pytest.mark.asyncio
async def test_tui_resume_banner_emits_backfill_events(tmp_path: Path) -> None:
    provider = MagicMock()
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    status_bus = StatusBus()
    config = _config()
    config["generation"] = {
        "wanted_chapters": 1,
        "seed": 12,
        "enable_outline_critique": False,
    }
    state = PipelineState(
        story_name="test-story",
        current_phase="outline",
        completed_phases=["init", "story-foundation"],
        outline_result=_outline_result(),
        completed_work_items={"outline": ["outline/draft"]},
        savepoints=["init", "story_foundation_complete"],
        status="running",
    )

    def fake_savepoint_path(story_name: str) -> Path:
        return tmp_path / story_name / "savepoints" / "pipeline_state.json"

    (tmp_path / "test-story").mkdir(parents=True, exist_ok=True)

    with (
        patch(
            "presentation.orchestrator._savepoint_path", side_effect=fake_savepoint_path
        ),
        patch("presentation.orchestrator.STORIES_DIR", tmp_path),
        patch("tools._io.STORIES_DIR", tmp_path),
        patch("presentation.orchestrator.OutlinePlannerAgent") as outline_cls,
        patch("presentation.orchestrator.StoryPlannerAgent") as arc_agent_cls,
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
        patch(
            "presentation.orchestrator._generate_character_sheets",
            new=AsyncMock(return_value=_generated_character_paths()),
        ),
        patch(
            "presentation.orchestrator._generate_setting_sheets",
            new=AsyncMock(return_value=[]),
        ),
    ):
        outline_cls.return_value.run = AsyncMock(return_value=_outline_result())
        arc_agent_cls.return_value.run = AsyncMock(
            return_value=ArcAnalysisResult(
                story_name="test-story",
                arc_assessment="Strong arc",
                verdict_code="strong",
                overall_score=0.9,
            )
        )
        chapter_cls.return_value.run = AsyncMock(return_value=_chapter_draft())
        wiki_cls.return_value.run = AsyncMock(return_value=_wiki_batch())
        consistency_cls.return_value.run = AsyncMock(
            return_value={"issues": [], "passed": True}
        )

        await _write_savepoint(state)

        await resume_pipeline(
            "test-story",
            None,
            NullApprovalGate(),
            bus,
            wiki_bus,
            config=config,
            provider=provider,
            status_bus=status_bus,
        )

    events = [event async for event in status_bus]
    assert any(
        event.phase == "story-foundation"
        and event.kind == "phase_end"
        and event.message == "(resumed)"
        for event in events
    )
    assert any(
        event.phase == "outline"
        and event.kind == "step"
        and event.message == "Resuming at: next step after outline/draft"
        for event in events
    )


@pytest.mark.asyncio
async def test_tui_resume_banner_suppressed_for_empty_ledger(tmp_path: Path) -> None:
    provider = MagicMock()
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    status_bus = StatusBus()
    config = _config()
    config["generation"] = {
        "wanted_chapters": 1,
        "seed": 12,
        "enable_outline_critique": False,
    }
    state = PipelineState(
        story_name="test-story",
        current_phase="outline",
        completed_phases=["init", "story-foundation"],
        outline_result=_outline_result(),
        completed_work_items={},
        savepoints=["init", "story_foundation_complete"],
        status="running",
    )

    def fake_savepoint_path(story_name: str) -> Path:
        return tmp_path / story_name / "savepoints" / "pipeline_state.json"

    (tmp_path / "test-story").mkdir(parents=True, exist_ok=True)

    with (
        patch(
            "presentation.orchestrator._savepoint_path", side_effect=fake_savepoint_path
        ),
        patch("presentation.orchestrator.STORIES_DIR", tmp_path),
        patch("tools._io.STORIES_DIR", tmp_path),
        patch("presentation.orchestrator.OutlinePlannerAgent") as outline_cls,
        patch("presentation.orchestrator.StoryPlannerAgent") as arc_agent_cls,
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
        patch(
            "presentation.orchestrator._generate_character_sheets",
            new=AsyncMock(return_value=_generated_character_paths()),
        ),
        patch(
            "presentation.orchestrator._generate_setting_sheets",
            new=AsyncMock(return_value=[]),
        ),
    ):
        outline_cls.return_value.run = AsyncMock(return_value=_outline_result())
        arc_agent_cls.return_value.run = AsyncMock(
            return_value=ArcAnalysisResult(
                story_name="test-story",
                arc_assessment="Strong arc",
                verdict_code="strong",
                overall_score=0.9,
            )
        )
        chapter_cls.return_value.run = AsyncMock(return_value=_chapter_draft())
        wiki_cls.return_value.run = AsyncMock(return_value=_wiki_batch())
        consistency_cls.return_value.run = AsyncMock(
            return_value={"issues": [], "passed": True}
        )

        await _write_savepoint(state)

        await resume_pipeline(
            "test-story",
            None,
            NullApprovalGate(),
            bus,
            wiki_bus,
            config=config,
            provider=provider,
            status_bus=status_bus,
        )

    events = [event async for event in status_bus]
    assert not any(event.message == "(resumed)" for event in events)
