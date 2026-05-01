import json
import inspect
import sys
from pathlib import Path

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


def test_outline_result_round_trip() -> None:
    state = PipelineState(
        story_name="test-story",
        current_phase="outline",
        outline_result=OutlineResult(
            story_name="test-story",
            chapter_outlines=[
                {"chapter_number": 1, "title": "Arrival", "summary": "Setup"}
            ],
            summary="Space opera setup",
            genre="science fiction",
            themes=["identity", "survival"],
            savepoint_id="outline-savepoint",
        ),
    )

    payload = state.to_dict()

    assert isinstance(payload, dict)
    assert PipelineState.from_dict(payload) == state


def test_chapter_draft_round_trip() -> None:
    state = PipelineState(
        story_name="test-story",
        current_phase="chapter-loop",
        approved_chapters=[
            ChapterDraft(
                story_name="test-story",
                chapter_number=1,
                title="Arrival",
                content="Chapter body",
                word_count=1234,
                savepoint_id="chapter-1-savepoint",
            )
        ],
    )

    assert PipelineState.from_dict(state.to_dict()) == state


def test_wiki_update_batch_round_trip() -> None:
    state = PipelineState(
        story_name="test-story",
        current_phase="wiki-update",
        wiki_batches=[
            WikiUpdateBatch(
                story_name="test-story",
                chapter_number=2,
                updated_pages=["captain-vela", "star-map"],
                new_pages=["outer-rim-station"],
                savepoint_id="wiki-batch-2",
            )
        ],
    )

    assert PipelineState.from_dict(state.to_dict()) == state


def test_approval_decision_defaults() -> None:
    decision = ApprovalDecision(approved=True)

    assert decision.feedback is None
    assert decision.auto_approved is False


def test_pipeline_state_round_trip_empty() -> None:
    state = PipelineState(story_name="test", current_phase="init")

    assert PipelineState.from_dict(state.to_dict()) == state


def test_pipeline_state_round_trip_full() -> None:
    state = PipelineState(
        story_name="test-story",
        current_phase="approval",
        completed_phases=["init", "outline", "chapter-loop"],
        outline_result=OutlineResult(
            story_name="test-story",
            chapter_outlines=[
                {"chapter_number": 1, "title": "Arrival", "summary": "Setup"},
                {"chapter_number": 2, "title": "Crossing", "summary": "Escalation"},
            ],
            summary="Crew enters unstable territory.",
            genre="science fiction",
            themes=["identity", "loyalty"],
            savepoint_id="outline-savepoint",
        ),
        approved_chapters=[
            ChapterDraft(
                story_name="test-story",
                chapter_number=1,
                title="Arrival",
                content="Chapter one body",
                word_count=1500,
                savepoint_id="chapter-1-savepoint",
            ),
            ChapterDraft(
                story_name="test-story",
                chapter_number=2,
                title="Crossing",
                content="Chapter two body",
                word_count=1650,
                savepoint_id="chapter-2-savepoint",
            ),
        ],
        wiki_batches=[
            WikiUpdateBatch(
                story_name="test-story",
                chapter_number=1,
                updated_pages=["captain-vela"],
                new_pages=["rift-gate"],
                savepoint_id="wiki-1",
            ),
            WikiUpdateBatch(
                story_name="test-story",
                chapter_number=2,
                updated_pages=["captain-vela", "rift-gate"],
                new_pages=["station-echo"],
                savepoint_id="wiki-2",
            ),
        ],
        batch_mode=True,
        savepoint_id="pipeline-savepoint",
    )

    round_tripped = PipelineState.from_dict(state.to_dict())

    assert round_tripped == state
    assert round_tripped.outline_result == state.outline_result
    assert round_tripped.approved_chapters == state.approved_chapters
    assert round_tripped.wiki_batches == state.wiki_batches


def test_pipeline_state_to_json_is_valid_json() -> None:
    state = PipelineState(
        story_name="test-story",
        current_phase="outline",
        completed_phases=["init"],
    )

    parsed = json.loads(state.to_json())

    assert isinstance(parsed, dict)
    assert parsed["story_name"] == "test-story"
    assert parsed["current_phase"] == "outline"


def test_all_handoff_types_importable() -> None:
    assert inspect.isclass(ApprovalDecision)
    assert inspect.isclass(ChapterDraft)
    assert inspect.isclass(OutlineResult)
    assert inspect.isclass(PipelineState)
    assert inspect.isclass(WikiUpdateBatch)


def test_outline_result_new_fields_defaults() -> None:
    result = OutlineResult(
        story_name="x",
        chapter_outlines=[],
        summary="",
        genre="",
        themes=[],
    )

    assert result.base_context == ""
    assert result.story_start_date == ""
    assert result.story_elements == ""
    assert result.chapter_skeletons == []
    assert result.chapter_details == []
    assert result.enrichment_suggestions == ""
    assert result.title == ""
    assert result.tags == []


def test_outline_result_new_fields_round_trip() -> None:
    original = OutlineResult(
        story_name="x",
        chapter_outlines=[{"chapter_number": 1, "title": "One", "summary": "Start"}],
        summary="summary",
        genre="genre",
        themes=["theme"],
        base_context="context",
        story_start_date="2024-01-15",
        story_elements="elements",
        chapter_skeletons=[{"chapter_number": 1, "beats": ["beat"]}],
        chapter_details=[{"chapter_number": 1, "detail": "detail"}],
        enrichment_suggestions="more detail",
        title="Title",
        tags=["tag-1", "tag-2"],
        savepoint_id="outline-savepoint",
    )
    state = PipelineState(
        story_name="x",
        current_phase="outline",
        outline_result=original,
    )

    round_tripped = PipelineState.from_dict(state.to_dict())

    assert round_tripped.outline_result == original


def test_chapter_draft_new_fields_defaults() -> None:
    draft = ChapterDraft(
        story_name="x",
        chapter_number=1,
        title="t",
        content="c",
        word_count=100,
    )

    assert draft.synopsis == ""
    assert draft.scene_definitions == []
    assert draft.recap == {}
    assert draft.consistency_findings == []
    assert draft.critic_findings == []


def test_chapter_draft_new_fields_round_trip() -> None:
    original = ChapterDraft(
        story_name="x",
        chapter_number=1,
        title="t",
        content="c",
        word_count=100,
        synopsis="synopsis",
        scene_definitions=[{"scene": 1, "summary": "opening"}],
        recap={"summary": "previously"},
        consistency_findings=[{"severity": "warning", "description": "drift"}],
        critic_findings=[{"severity": "info", "description": "tighten prose"}],
        savepoint_id="chapter-savepoint",
    )
    state = PipelineState(
        story_name="x",
        current_phase="chapter-loop",
        approved_chapters=[original],
    )

    round_tripped = PipelineState.from_dict(state.to_dict())

    assert round_tripped.approved_chapters == [original]


def test_pipeline_state_new_fields_defaults() -> None:
    state = PipelineState(story_name="x", current_phase="init")

    assert state.critic_summary == ""
    assert state.recaps == {}
    assert state.evolved_sheets == {}


def test_pipeline_state_new_fields_round_trip() -> None:
    state = PipelineState(
        story_name="x",
        current_phase="review",
        critic_summary="Needs revision",
        recaps={"chapter_1": {"summary": "recap"}},
        evolved_sheets={"characters": {"aria": {"trait": "brave"}}},
    )

    round_tripped = PipelineState.from_dict(state.to_dict())

    assert round_tripped.critic_summary == "Needs revision"
    assert round_tripped.recaps == {"chapter_1": {"summary": "recap"}}
    assert round_tripped.evolved_sheets == {"characters": {"aria": {"trait": "brave"}}}


def test_old_state_json_loads_without_error() -> None:
    data = {
        "story_name": "old-story",
        "current_phase": "outline",
        "outline_result": {
            "story_name": "old-story",
            "chapter_outlines": [],
            "summary": "s",
            "genre": "g",
            "themes": [],
        },
        "approved_chapters": [
            {
                "story_name": "old-story",
                "chapter_number": 1,
                "title": "t",
                "content": "c",
                "word_count": 100,
            }
        ],
    }

    state = PipelineState.from_dict(data)

    assert state.outline_result is not None
    assert state.outline_result.base_context == ""
    assert state.approved_chapters[0].synopsis == ""
    assert state.critic_summary == ""
