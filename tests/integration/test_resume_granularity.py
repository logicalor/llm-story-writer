"""Integration tests for granular interrupt + resume checkpoint behavior."""

from __future__ import annotations

import sys
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Any, Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from application.pipeline.handoffs import (
    ArcAnalysisResult,
    ChapterDraft,
    FinalEditResult,
    OutlineResult,
    PipelineState,
    WikiUpdateBatch,
)
from presentation.orchestrator import (
    NullApprovalGate,
    TokenStreamBus,
    WikiContextBus,
    _write_savepoint,
    resume_pipeline,
    run_pipeline,
)


def _config() -> dict[str, object]:
    return {
        "generation": {
            "wanted_chapters": 1,
            "seed": 12,
            "enable_final_edit": True,
        },
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


def _outline_result(story_name: str = "test-story") -> OutlineResult:
    """Minimal 1-chapter outline."""
    return OutlineResult(
        story_name=story_name,
        chapter_outlines=[
            {"chapter_number": 1, "title": "Chapter 1", "summary": "Intro"}
        ],
        summary="Story summary",
        genre="science fiction",
        themes=["memory"],
    )


def _chapter_draft(
    story_name: str = "test-story",
    content: str = "Chapter one draft.",
) -> ChapterDraft:
    """Minimal chapter draft."""
    return ChapterDraft(
        story_name=story_name,
        chapter_number=1,
        title="Chapter 1",
        content=content,
        word_count=len(content.split()),
    )


def _final_edit_result(
    story_name: str = "test-story",
    content: str = "Chapter one final.",
) -> FinalEditResult:
    return FinalEditResult(
        story_name=story_name,
        chapters_processed=1,
        total_issues_found=0,
        total_revisions_made=1,
        edited_chapters=[_chapter_draft(story_name, content)],
    )


def _wiki_batch(story_name: str = "test-story") -> WikiUpdateBatch:
    """Minimal wiki update batch."""
    return WikiUpdateBatch(
        story_name=story_name,
        chapter_number=1,
        updated_pages=[],
        new_pages=[],
    )


def _arc_result(story_name: str = "test-story") -> ArcAnalysisResult:
    """Minimal arc analysis result."""
    return ArcAnalysisResult(
        story_name=story_name,
        arc_assessment="Arc looks coherent.",
        verdict_code="strong",
        overall_score=0.95,
    )


def _story_metadata_result(story_name: str = "test-story") -> MagicMock:
    return MagicMock(
        title="Title", summary="Summary", tags=["tag"], story_name=story_name
    )


def _generated_wiki_result(generated: int, skipped: int = 0) -> dict[str, int]:
    return {"generated": generated, "skipped": skipped}


def _savepoint_names() -> list[str]:
    return [
        "init",
        "story_foundation_complete",
        "outline",
        "metadata_outline_complete",
        "arc_analysis_complete",
        "wiki-generation",
        "wiki_populated",
        "chapter-1",
        "chapter-loop",
        "final_edit_complete",
    ]


def _phase_prefix_after_wiki_generation() -> list[str]:
    return [
        "init",
        "story-foundation",
        "outline",
        "metadata-outline",
        "narrative-arc",
        "wiki-generation",
        "wiki-bootstrap",
    ]


def _phase_prefix_after_chapter_loop() -> list[str]:
    return _phase_prefix_after_wiki_generation() + [
        "metadata-chapter-1",
        "chapter-1",
        "chapter-loop",
    ]


@contextmanager
def _patched_pipeline(
    tmp_path: Path,
    *,
    story_name: str,
    draft_content: str = "Chapter one draft.",
    final_content: str = "Chapter one final.",
) -> Iterator[dict[str, Any]]:
    provider = MagicMock()
    provider.generate_text = AsyncMock(return_value='["Alice"]')

    def fake_savepoint_path(name: str) -> Path:
        return tmp_path / name / "savepoints" / "pipeline_state.json"

    with ExitStack() as stack:
        stack.enter_context(
            patch(
                "presentation.orchestrator._savepoint_path",
                side_effect=fake_savepoint_path,
            )
        )
        stack.enter_context(patch("presentation.orchestrator.STORIES_DIR", tmp_path))
        stack.enter_context(patch("tools._io.STORIES_DIR", tmp_path))
        stack.enter_context(
            patch("presentation.agents.chapter_writer.STORIES_DIR", tmp_path)
        )

        foundation_cls = stack.enter_context(
            patch("presentation.orchestrator.StoryFoundationAgent")
        )
        outline_cls = stack.enter_context(
            patch("presentation.orchestrator.OutlinePlannerAgent")
        )
        planner_cls = stack.enter_context(
            patch("presentation.orchestrator.StoryPlannerAgent")
        )
        chapter_cls = stack.enter_context(
            patch("presentation.orchestrator.ChapterWriterAgent")
        )
        wiki_cls = stack.enter_context(
            patch("presentation.orchestrator.WikiMaintainerAgent")
        )
        consistency_cls = stack.enter_context(
            patch("presentation.orchestrator.ConsistencyCheckerAgent")
        )
        final_editor_cls = stack.enter_context(
            patch("presentation.orchestrator.FinalEditorAgent")
        )
        metadata_cls = stack.enter_context(
            patch("presentation.orchestrator.StoryMetadataAgent")
        )
        recap_cls = stack.enter_context(
            patch("presentation.agents.recap_writer.RecapWriterAgent")
        )
        generate_char_pages = MagicMock(return_value={"generated": 2, "skipped": 0})
        generate_location_pages = MagicMock(return_value={"generated": 3, "skipped": 0})
        stack.enter_context(
            patch(
                "tools.wiki_generation.generate_character_pages",
                new=generate_char_pages,
            )
        )
        stack.enter_context(
            patch(
                "tools.wiki_generation.generate_location_pages",
                new=generate_location_pages,
            )
        )
        stack.enter_context(
            patch(
                "presentation.orchestrator._init_wiki_for_story",
                return_value={"status": "ok"},
            )
        )
        stack.enter_context(
            patch(
                "presentation.orchestrator._list_wiki_entities",
                return_value=[{"name": "Alice"}],
            )
        )
        stack.enter_context(
            patch("presentation.orchestrator._bootstrap_single_wiki_entity")
        )

        foundation_cls.return_value.run = AsyncMock(
            return_value=_outline_result(story_name)
        )
        outline_cls.return_value.run = AsyncMock(
            return_value=_outline_result(story_name)
        )
        planner_cls.return_value.run = AsyncMock(return_value=_arc_result(story_name))
        chapter_cls.return_value.run = AsyncMock(
            return_value=_chapter_draft(story_name, draft_content)
        )
        wiki_cls.return_value.run = AsyncMock(return_value=_wiki_batch(story_name))
        consistency_cls.return_value.run = AsyncMock(
            return_value={"issues": [], "passed": True}
        )
        recap_cls.return_value.run = AsyncMock(
            return_value={
                "events": "Event one.",
                "compact": "Compact recap.",
                "sanitised": "Sanitised recap.",
            }
        )
        metadata_cls.return_value.run = AsyncMock(
            return_value=_story_metadata_result(story_name)
        )
        final_editor_cls.return_value.build_prior_summaries = MagicMock(
            return_value=[""]
        )
        final_editor_cls.return_value.edit_single_chapter = AsyncMock(
            return_value=_chapter_draft(story_name, final_content)
        )

        yield {
            "provider": provider,
            "foundation": foundation_cls.return_value.run,
            "outline": outline_cls.return_value.run,
            "arc": planner_cls.return_value.run,
            "chapter_writer": chapter_cls.return_value.run,
            "wiki": wiki_cls.return_value.run,
            "consistency": consistency_cls.return_value.run,
            "wiki_generation_characters": generate_char_pages,
            "wiki_generation_locations": generate_location_pages,
            "recap": recap_cls.return_value.run,
            "metadata": metadata_cls.return_value.run,
            "final_edit": final_editor_cls.return_value.edit_single_chapter,
        }


def _await_counts(mocks: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for key, value in mocks.items():
        if isinstance(value, AsyncMock):
            counts[key] = value.await_count
        elif isinstance(value, MagicMock):
            counts[key] = value.call_count
    return counts


def _total_llm_calls(mocks: dict[str, Any]) -> int:
    counts = _await_counts(mocks)
    return sum(count for key, count in counts.items() if key != "provider")


async def _run_baseline(
    tmp_path: Path,
    *,
    story_name: str,
    draft_content: str = "Chapter one draft.",
    final_content: str = "Chapter one final.",
) -> tuple[PipelineState, dict[str, int], str]:
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    with _patched_pipeline(
        tmp_path,
        story_name=story_name,
        draft_content=draft_content,
        final_content=final_content,
    ) as mocks:
        state = await run_pipeline(
            story_name,
            NullApprovalGate(),
            bus,
            wiki_bus,
            config=_config(),
            provider=mocks["provider"],
        )
        counts = _await_counts(mocks)
    output = (tmp_path / story_name / "output" / "story.md").read_text(encoding="utf-8")
    return state, counts, output


async def _resume_from_partial(
    tmp_path: Path,
    *,
    story_name: str,
    state: PipelineState,
    draft_content: str = "Chapter one draft.",
    final_content: str = "Chapter one final.",
    chapter_file_content: str | None = None,
    edited_file_content: str | None = None,
) -> tuple[PipelineState, dict[str, int], str]:
    bus = TokenStreamBus()
    wiki_bus = WikiContextBus()
    with _patched_pipeline(
        tmp_path,
        story_name=story_name,
        draft_content=draft_content,
        final_content=final_content,
    ) as mocks:
        story_dir = tmp_path / story_name
        story_dir.mkdir(parents=True, exist_ok=True)
        chapters_dir = story_dir / "chapters"
        chapters_dir.mkdir(parents=True, exist_ok=True)
        if chapter_file_content is not None:
            (chapters_dir / "chapter_1.md").write_text(
                chapter_file_content,
                encoding="utf-8",
            )
        if edited_file_content is not None:
            (chapters_dir / "chapter_1_edited.md").write_text(
                edited_file_content,
                encoding="utf-8",
            )

        await _write_savepoint(state)
        resumed = await resume_pipeline(
            story_name,
            None,
            NullApprovalGate(),
            bus,
            wiki_bus,
            config=_config(),
            provider=mocks["provider"],
        )
        counts = _await_counts(mocks)
    output = (tmp_path / story_name / "output" / "story.md").read_text(encoding="utf-8")
    return resumed, counts, output


def _state_after_wiki_generation(story_name: str) -> PipelineState:
    return PipelineState(
        story_name=story_name,
        current_phase="wiki-generation",
        completed_phases=_phase_prefix_after_wiki_generation(),
        outline_result=_outline_result(story_name),
        completed_work_items={},
        savepoints=_savepoint_names(),
        status="running",
    )


def _state_after_chapter_draft(
    story_name: str,
    draft_content: str,
) -> PipelineState:
    return PipelineState(
        story_name=story_name,
        current_phase="chapter-1",
        completed_phases=_phase_prefix_after_wiki_generation(),
        outline_result=_outline_result(story_name),
        approved_chapters=[_chapter_draft(story_name, draft_content)],
        completed_work_items={"chapter-1": ["chapter-1/draft"]},
        savepoints=_savepoint_names(),
        status="running",
    )


def _state_after_final_edit(
    story_name: str,
    draft_content: str,
) -> PipelineState:
    return PipelineState(
        story_name=story_name,
        current_phase="final-edit",
        completed_phases=_phase_prefix_after_chapter_loop(),
        outline_result=_outline_result(story_name),
        approved_chapters=[_chapter_draft(story_name, draft_content)],
        completed_work_items={
            "chapter-1": [
                "chapter-1/draft",
                "chapter-1/consistency-check",
                "chapter-1/wiki-update",
                "chapter-1/recap",
                "chapter-1/metadata",
            ],
            "final-edit": ["final-edit/chapter:1"],
        },
        savepoints=_savepoint_names(),
        status="running",
    )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_baseline_run_completes_successfully(tmp_path: Path) -> None:
    state, counts, output = await _run_baseline(tmp_path, story_name="test-story")

    assert state.status == "complete"
    assert state.approved_chapters
    assert output == "Chapter one final.\n"
    assert counts["chapter_writer"] == 1
    assert counts.get("char_evolver", 0) == 0
    assert counts.get("setting_evolver", 0) == 0
    assert counts["final_edit"] == 1


@pytest.mark.asyncio
@pytest.mark.integration
async def test_resume_after_wiki_generation_phase_interrupt(tmp_path: Path) -> None:
    baseline_state, baseline_counts, baseline_output = await _run_baseline(
        tmp_path,
        story_name="baseline-story",
    )

    resumed_state, resumed_counts, resumed_output = await _resume_from_partial(
        tmp_path,
        story_name="resume-story",
        state=_state_after_wiki_generation("resume-story"),
    )

    assert resumed_state.status == "complete"
    assert (
        resumed_state.approved_chapters[0].content
        == baseline_state.approved_chapters[0].content
    )
    assert resumed_output == baseline_output
    assert resumed_counts["wiki_generation_characters"] == 0
    assert resumed_counts["wiki_generation_locations"] == 0
    assert resumed_counts["chapter_writer"] == baseline_counts["chapter_writer"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_resume_after_chapter_draft_interrupt(tmp_path: Path) -> None:
    draft_content = "Chapter one draft."
    baseline_state, _, baseline_output = await _run_baseline(
        tmp_path,
        story_name="baseline-story",
        draft_content=draft_content,
    )

    resumed_state, resumed_counts, resumed_output = await _resume_from_partial(
        tmp_path,
        story_name="resume-story",
        state=_state_after_chapter_draft("resume-story", draft_content),
        draft_content=draft_content,
        chapter_file_content=draft_content,
    )

    assert resumed_state.status == "complete"
    assert (
        resumed_state.approved_chapters[0].content
        == baseline_state.approved_chapters[0].content
    )
    assert resumed_output == baseline_output
    assert resumed_counts["chapter_writer"] == 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_resume_after_final_edit_interrupt(tmp_path: Path) -> None:
    draft_content = "Chapter one draft."
    final_content = "Chapter one final."
    baseline_state, _, baseline_output = await _run_baseline(
        tmp_path,
        story_name="baseline-story",
        draft_content=draft_content,
        final_content=final_content,
    )

    resumed_state, resumed_counts, resumed_output = await _resume_from_partial(
        tmp_path,
        story_name="resume-story",
        state=_state_after_final_edit("resume-story", draft_content),
        draft_content=draft_content,
        final_content=final_content,
        edited_file_content=final_content,
    )

    assert resumed_state.status == "complete"
    assert resumed_counts["final_edit"] == 0
    assert (
        resumed_state.approved_chapters[0].content
        == baseline_state.approved_chapters[0].content
    )
    assert resumed_output == baseline_output


@pytest.mark.asyncio
@pytest.mark.integration
async def test_total_llm_calls_no_duplicates_across_interrupt_resume(
    tmp_path: Path,
) -> None:
    _, baseline_counts, _ = await _run_baseline(tmp_path, story_name="baseline-story")

    _, wiki_generation_resume_counts, _ = await _resume_from_partial(
        tmp_path,
        story_name="resume-wiki-generation-story",
        state=_state_after_wiki_generation("resume-wiki-generation-story"),
    )
    _, chapter_resume_counts, _ = await _resume_from_partial(
        tmp_path,
        story_name="resume-draft-story",
        state=_state_after_chapter_draft("resume-draft-story", "Chapter one draft."),
        chapter_file_content="Chapter one draft.",
    )
    _, final_resume_counts, _ = await _resume_from_partial(
        tmp_path,
        story_name="resume-final-story",
        state=_state_after_final_edit("resume-final-story", "Chapter one draft."),
        edited_file_content="Chapter one final.",
    )

    baseline_chapter_calls = baseline_counts["chapter_writer"]

    assert baseline_chapter_calls == 1
    assert 0 + wiki_generation_resume_counts["chapter_writer"] == baseline_chapter_calls
    assert 1 + chapter_resume_counts["chapter_writer"] == baseline_chapter_calls
    assert 1 + final_resume_counts["chapter_writer"] == baseline_chapter_calls
