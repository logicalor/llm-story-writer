import sys
from pathlib import Path
from unittest.mock import call, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from domain.exceptions import StoryGenerationError
from tools.context_assembly import assemble_context


def _recap_row(
    row_id: str,
    document: str,
    *,
    chapter: int = 1,
) -> dict:
    return {
        "id": row_id,
        "document": document,
        "metadata": {
            "chapter": chapter,
            "kind": "aggregate",
            "story": "test-story",
            "participants": "",
            "locations": "",
        },
    }


def test_returns_dict_with_expected_keys() -> None:
    with patch("tools.context_assembly.get_snapshot", return_value="# Wiki\nContent"):
        with patch(
            "tools.context_assembly.query_recap",
            return_value=[_recap_row("aggregate/1", "alpha beta gamma", chapter=1)],
        ):
            result = assemble_context(
                "test-story",
                scope="scene",
                focus="a scene",
            )

    assert set(result) == {"wiki_snapshot", "recap_snippets"}
    assert isinstance(result["wiki_snapshot"], str)
    assert isinstance(result["recap_snippets"], list)


def test_wiki_budget_capped_at_scope_default() -> None:
    with patch(
        "tools.context_assembly.get_snapshot", return_value="# Wiki"
    ) as mock_snap:
        with patch("tools.context_assembly.query_recap", return_value=[]):
            assemble_context(
                "test-story",
                scope="outline",
                focus="outline focus",
                recap_window=("none", 0),
                token_budget=100000,
            )

    assert mock_snap.call_args.kwargs["budget"] == 6000


def test_wiki_budget_capped_by_token_budget_70_percent() -> None:
    with patch(
        "tools.context_assembly.get_snapshot", return_value="# Wiki"
    ) as mock_snap:
        with patch("tools.context_assembly.query_recap", return_value=[]):
            assemble_context(
                "test-story",
                scope="chapter",
                focus="chapter focus",
                recap_window=("none", 0),
                token_budget=10000,
            )

    assert mock_snap.call_args.kwargs["budget"] == 7000


def test_recap_budget_is_30_percent_of_token_budget() -> None:
    rows = [
        _recap_row("aggregate/1", "alpha beta gamma", chapter=3),
        _recap_row("aggregate/2", "delta epsilon zeta", chapter=2),
        _recap_row("aggregate/3", "eta theta iota", chapter=1),
    ]

    with patch("tools.context_assembly.get_snapshot", return_value="# Wiki"):
        with patch("tools.context_assembly.query_recap", return_value=rows):
            result = assemble_context(
                "test-story",
                scope="scene",
                focus="scene focus",
                recap_window=("semantic", 3),
                token_budget=20,
            )

    assert result["recap_snippets"] == [
        "alpha beta gamma",
        "delta epsilon zeta",
    ]


def test_empty_wiki_non_initial_scope_emits_warning(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with patch("tools.context_assembly.get_snapshot", return_value=None):
        with patch("tools.context_assembly.query_recap", return_value=[]):
            result = assemble_context(
                "test-story",
                scope="scene",
                focus="scene focus",
                recap_window=("none", 0),
            )

    captured = capsys.readouterr()
    assert result["wiki_snapshot"] == ""
    assert "wiki snapshot empty" in captured.err
    assert "scope='scene'" in captured.err


def test_empty_wiki_initial_scope_no_warning(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with patch("tools.context_assembly.get_snapshot", return_value=None):
        with patch("tools.context_assembly.query_recap", return_value=[]):
            result = assemble_context(
                "test-story",
                scope="outline",
                focus="outline focus",
                recap_window=("none", 0),
            )

    captured = capsys.readouterr()
    assert result["wiki_snapshot"] == ""
    assert captured.err == ""


def test_fatal_scope_wiki_none_raises_story_generation_error() -> None:
    with patch("tools.context_assembly.get_snapshot", return_value=None):
        with patch("tools.context_assembly.query_recap", return_value=[]):
            with pytest.raises(StoryGenerationError, match="Wiki snapshot unavailable"):
                assemble_context(
                    "test-story",
                    scope="chapter",
                    focus="chapter focus",
                    recap_window=("none", 0),
                )


def test_fatal_scope_recap_exception_raises_story_generation_error() -> None:
    with patch("tools.context_assembly.get_snapshot", return_value="# Wiki"):
        with patch(
            "tools.context_assembly.query_recap",
            side_effect=RuntimeError("chroma offline"),
        ):
            with pytest.raises(StoryGenerationError, match="Recap retrieval failed"):
                assemble_context(
                    "test-story",
                    scope="consistency",
                    focus="consistency focus",
                    recap_window=("semantic", 3),
                )


def test_non_fatal_scope_recap_exception_returns_empty_list() -> None:
    with patch("tools.context_assembly.get_snapshot", return_value="# Wiki"):
        with patch(
            "tools.context_assembly.query_recap",
            side_effect=RuntimeError("chroma offline"),
        ):
            result = assemble_context(
                "test-story",
                scope="scene",
                focus="scene focus",
                recap_window=("semantic", 3),
            )

    assert result["wiki_snapshot"] == "# Wiki"
    assert result["recap_snippets"] == []


def test_recap_window_none_returns_empty_list() -> None:
    with patch("tools.context_assembly.get_snapshot", return_value="# Wiki"):
        with patch("tools.context_assembly.query_recap") as mock_query:
            result = assemble_context(
                "test-story",
                scope="scene",
                focus="scene focus",
                recap_window=("none", 0),
            )

    assert result["recap_snippets"] == []
    mock_query.assert_not_called()


def test_recap_window_semantic_calls_query_with_query_text() -> None:
    rows = [_recap_row("aggregate/1", "alpha beta gamma", chapter=1)]

    with patch("tools.context_assembly.get_snapshot", return_value="# Wiki"):
        with patch(
            "tools.context_assembly.query_recap", return_value=rows
        ) as mock_query:
            assemble_context(
                "test-story",
                scope="scene",
                focus="search terms",
                recap_window=("semantic", 3),
            )

    mock_query.assert_called_once_with(
        "test-story",
        query_text="search terms",
        n_results=3,
    )


def test_recap_window_character_deduplicates() -> None:
    alice_rows = [
        _recap_row("aggregate/shared", "shared doc", chapter=4),
        _recap_row("aggregate/alice", "alice only", chapter=2),
    ]
    bob_rows = [
        _recap_row("aggregate/shared", "shared doc", chapter=4),
        _recap_row("aggregate/bob", "bob only", chapter=3),
    ]

    with patch("tools.context_assembly.get_snapshot", return_value="# Wiki"):
        with patch(
            "tools.context_assembly.query_recap",
            side_effect=[alice_rows, bob_rows],
        ) as mock_query:
            result = assemble_context(
                "test-story",
                scope="scene",
                focus="character focus",
                characters=("alice", "bob"),
                recap_window=("character", 3),
                token_budget=30,
            )

    assert result["recap_snippets"] == ["shared doc", "bob only", "alice only"]
    assert mock_query.call_args_list == [
        call("test-story", character="alice"),
        call("test-story", character="bob"),
    ]


def test_recap_window_chapter_uses_chapter_range() -> None:
    rows = [_recap_row("aggregate/1", "alpha beta gamma", chapter=4)]

    with patch("tools.context_assembly.get_snapshot", return_value="# Wiki"):
        with patch(
            "tools.context_assembly.query_recap", return_value=rows
        ) as mock_query:
            assemble_context(
                "test-story",
                scope="scene",
                focus="chapter focus",
                chapter=5,
                recap_window=("chapter", 3),
            )

    mock_query.assert_called_once_with("test-story", chapter_range=(2, 4))


def test_recap_window_chapter_fallback_no_chapter() -> None:
    rows = [_recap_row("aggregate/1", "alpha beta gamma", chapter=1)]

    with patch("tools.context_assembly.get_snapshot", return_value="# Wiki"):
        with patch(
            "tools.context_assembly.query_recap", return_value=rows
        ) as mock_query:
            assemble_context(
                "test-story",
                scope="scene",
                focus="chapter focus",
                chapter=None,
                recap_window=("chapter", 3),
            )

    mock_query.assert_called_once_with("test-story")


def test_recap_window_location_queries_per_location_slug() -> None:
    tavern_rows = [_recap_row("aggregate/tavern", "tavern doc", chapter=2)]
    docks_rows = [_recap_row("aggregate/docks", "docks doc", chapter=3)]

    with patch("tools.context_assembly.get_snapshot", return_value="# Wiki"):
        with patch(
            "tools.context_assembly.query_recap",
            side_effect=[tavern_rows, docks_rows],
        ) as mock_query:
            result = assemble_context(
                "test-story",
                scope="scene",
                focus="location focus",
                locations=("tavern", "docks"),
                recap_window=("location", 2),
            )

    assert result["recap_snippets"] == ["docks doc", "tavern doc"]
    assert mock_query.call_args_list == [
        call("test-story", location="tavern"),
        call("test-story", location="docks"),
    ]


def test_recap_budget_truncates_snippets() -> None:
    rows = [
        _recap_row("aggregate/1", "alpha beta", chapter=3),
        _recap_row("aggregate/2", "gamma delta", chapter=2),
    ]

    with patch("tools.context_assembly.get_snapshot", return_value="# Wiki"):
        with patch("tools.context_assembly.query_recap", return_value=rows):
            result = assemble_context(
                "test-story",
                scope="scene",
                focus="scene focus",
                recap_window=("semantic", 2),
                token_budget=12,
            )

    assert result["recap_snippets"] == ["alpha beta"]


@pytest.mark.parametrize(
    "scope",
    [
        "outline",
        "chapter",
        "scene",
        "consistency",
        "recap",
        "metadata",
        "final_edit",
    ],
)
def test_all_scopes_return_valid_structure(scope: str) -> None:
    rows = [_recap_row("aggregate/1", "alpha beta gamma", chapter=1)]

    with patch("tools.context_assembly.get_snapshot", return_value="# Wiki"):
        with patch("tools.context_assembly.query_recap", return_value=rows):
            result = assemble_context(
                "test-story",
                scope=scope,
                focus=f"{scope} focus",
            )

    assert set(result) == {"wiki_snapshot", "recap_snippets"}
    assert isinstance(result["wiki_snapshot"], str)
    assert isinstance(result["recap_snippets"], list)
