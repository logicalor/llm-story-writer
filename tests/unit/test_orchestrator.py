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
            new=AsyncMock(return_value=[]),
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
            new=AsyncMock(return_value=[]),
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
        patch("presentation.orchestrator.OutlinePlannerAgent") as outline_cls,
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
        patch(
            "presentation.orchestrator._generate_character_sheets",
            new=AsyncMock(return_value=[]),
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
            new=AsyncMock(return_value=[]),
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
            new=AsyncMock(return_value=[]),
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
        patch("presentation.orchestrator.STORIES_DIR", tmp_path),
        patch("tools._io.STORIES_DIR", tmp_path),
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
        patch(
            "presentation.orchestrator._generate_character_sheets",
            new=AsyncMock(return_value=[]),
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
            new=AsyncMock(return_value=[]),
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
            "# Bob\nSidekick.",
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
    written = list(characters_dir.glob("*.json"))
    assert len(written) == 2
    names_written = {
        json.loads(path.read_text(encoding="utf-8"))["name"] for path in written
    }
    assert names_written == {"Alice", "Bob"}


@pytest.mark.asyncio
async def test_characters_phase_skips_failed_sheet_generation(tmp_path: Path) -> None:
    provider = MagicMock()
    provider.generate_text = AsyncMock(
        side_effect=[
            '["Alice", "Bob"]',
            RuntimeError("LLM error"),
            "# Bob\nSidekick.",
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
    assert {path.name for path in characters_dir.glob("*.json")} == {"bob.json"}


@pytest.mark.asyncio
async def test_settings_phase_writes_sheets_to_disk(tmp_path: Path) -> None:
    """Settings phase writes setting sheet JSON files to disk."""
    provider = MagicMock()
    provider.generate_text = AsyncMock(
        side_effect=[
            '["The Citadel", "Dark Forest"]',
            "# The Citadel\nA fortified city.",
            "# Dark Forest\nA mysterious woodland.",
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
        patch("presentation.orchestrator.OutlinePlannerAgent") as outline_cls,
        patch("presentation.orchestrator.ChapterWriterAgent") as chapter_cls,
        patch("presentation.orchestrator.WikiMaintainerAgent") as wiki_cls,
        patch("presentation.orchestrator.ConsistencyCheckerAgent") as consistency_cls,
        patch(
            "presentation.orchestrator._generate_character_sheets",
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

    settings_dir = tmp_path / "test-story" / "settings"
    assert settings_dir.exists()
    written = list(settings_dir.glob("*.json"))
    assert len(written) == 2
    names_written = {
        json.loads(path.read_text(encoding="utf-8"))["name"] for path in written
    }
    assert names_written == {"The Citadel", "Dark Forest"}


@pytest.mark.asyncio
async def test_characters_phase_graceful_on_invalid_json(tmp_path: Path) -> None:
    """Characters phase handles malformed LLM names response gracefully."""
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
            new=AsyncMock(return_value=[]),
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
            new=AsyncMock(return_value=[]),
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
            new=AsyncMock(return_value=[]),
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
                edited_chapters=[
                    ChapterDraft(
                        story_name="test-story",
                        chapter_number=1,
                        title="Chapter 1",
                        content="Edited content",
                        word_count=2,
                    )
                ],
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

    final_editor_cls.return_value.run.assert_awaited_once()
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
            new=AsyncMock(return_value=[]),
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
        final_editor_cls.return_value.run = AsyncMock(
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
    final_editor_cls.return_value.run.assert_awaited_once()
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
            new=AsyncMock(return_value=[]),
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
            new=AsyncMock(return_value=[]),
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
            new=AsyncMock(return_value=[]),
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
            new=AsyncMock(return_value=[]),
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
            new=AsyncMock(return_value=[]),
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
