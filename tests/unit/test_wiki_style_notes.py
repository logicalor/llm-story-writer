"""Unit tests for wiki_style_notes promotion tool."""

from __future__ import annotations

import json
from pathlib import Path


from tools._wiki import parse_frontmatter
from tools.wiki_style_notes import promote_findings


def _story_dir(base: Path, name: str = "test-story") -> Path:
    story_dir = base / name
    story_dir.mkdir(parents=True, exist_ok=True)
    return story_dir


def _write_lessons(base: Path, name: str, chapter: int, lessons: dict) -> None:
    path = base / name / "chapters" / f"chapter_{chapter}" / "critique_lessons.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(lessons))


def _style_notes_path(base: Path, name: str = "test-story") -> Path:
    return base / name / "wiki" / "style-notes.md"


def _write_existing_style_notes(
    base: Path, content: str, name: str = "test-story"
) -> Path:
    path = _style_notes_path(base, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def test_no_lessons_returns_not_written(tmp_path: Path) -> None:
    _story_dir(tmp_path)
    _write_lessons(tmp_path, "test-story", 1, {})
    _write_lessons(tmp_path, "test-story", 2, {})
    _write_lessons(tmp_path, "test-story", 3, {})

    result = promote_findings("test-story", 3, stories_dir=tmp_path)

    assert result == {"written": False, "promoted": []}
    assert not _style_notes_path(tmp_path).exists()


def test_single_chapter_finding_not_promoted(tmp_path: Path) -> None:
    _story_dir(tmp_path)
    _write_lessons(tmp_path, "test-story", 1, {"style_violations": 2})

    result = promote_findings("test-story", 1, stories_dir=tmp_path)

    assert result == {"written": False, "promoted": []}
    assert not _style_notes_path(tmp_path).exists()


def test_two_chapter_finding_promoted(tmp_path: Path) -> None:
    _story_dir(tmp_path)
    _write_lessons(tmp_path, "test-story", 1, {"style_violations": 1})
    _write_lessons(tmp_path, "test-story", 2, {"style_violations": 3})

    result = promote_findings("test-story", 2, stories_dir=tmp_path)

    style_notes_path = _style_notes_path(tmp_path)
    assert result == {"written": True, "promoted": ["style_violations"]}
    assert style_notes_path.exists()
    assert "### style_violations" in style_notes_path.read_text()


def test_three_chapters_same_finding_creates_file(tmp_path: Path) -> None:
    _story_dir(tmp_path)
    _write_lessons(tmp_path, "test-story", 1, {"style_violations": 1})
    _write_lessons(tmp_path, "test-story", 2, {"style_violations": 2})
    _write_lessons(tmp_path, "test-story", 3, {"style_violations": 1})

    result = promote_findings("test-story", 3, stories_dir=tmp_path)

    style_notes_path = _style_notes_path(tmp_path)
    assert result == {"written": True, "promoted": ["style_violations"]}
    assert style_notes_path.exists()

    frontmatter, body = parse_frontmatter(style_notes_path.read_text())
    assert frontmatter["type"] == "style_notes"
    assert frontmatter["slug"] == "style-notes"
    assert "last_updated" in frontmatter
    assert body.startswith("# Style Notes")
    assert "Flagged in chapters: 1, 2, 3" in body


def test_pinned_page_not_updated(tmp_path: Path) -> None:
    _story_dir(tmp_path)
    _write_lessons(tmp_path, "test-story", 1, {"style_violations": 1})
    _write_lessons(tmp_path, "test-story", 2, {"style_violations": 1})
    existing = "---\ntype: style_notes\nslug: style-notes\npinned: true\nversion: 4\n---\n\noriginal body\n"
    style_notes_path = _write_existing_style_notes(tmp_path, existing)

    result = promote_findings("test-story", 2, stories_dir=tmp_path)

    assert result == {"written": False, "promoted": []}
    assert style_notes_path.read_text() == existing


def test_suppress_flag_preserved_on_update(tmp_path: Path) -> None:
    _story_dir(tmp_path)
    _write_lessons(tmp_path, "test-story", 1, {"style_violations": 1})
    _write_lessons(tmp_path, "test-story", 2, {"style_violations": 1})
    _write_existing_style_notes(
        tmp_path,
        "---\ntype: style_notes\nslug: style-notes\nsuppress: true\nversion: 1\n---\n\nold body\n",
    )

    result = promote_findings("test-story", 2, stories_dir=tmp_path)

    frontmatter, body = parse_frontmatter(_style_notes_path(tmp_path).read_text())
    assert result == {"written": True, "promoted": ["style_violations"]}
    assert frontmatter["suppress"] is True
    assert frontmatter["version"] == 2
    assert "### style_violations" in body


def test_version_increments_on_update(tmp_path: Path) -> None:
    _story_dir(tmp_path)
    _write_lessons(tmp_path, "test-story", 1, {"style_violations": 1})
    _write_lessons(tmp_path, "test-story", 2, {"style_violations": 1})
    _write_existing_style_notes(
        tmp_path,
        "---\ntype: style_notes\nslug: style-notes\nversion: 1\n---\n\nold body\n",
    )

    result = promote_findings("test-story", 2, stories_dir=tmp_path)

    frontmatter, _ = parse_frontmatter(_style_notes_path(tmp_path).read_text())
    assert result == {"written": True, "promoted": ["style_violations"]}
    assert frontmatter["version"] == 2


def test_only_criteria_in_two_plus_chapters_promoted(tmp_path: Path) -> None:
    _story_dir(tmp_path)
    _write_lessons(
        tmp_path,
        "test-story",
        1,
        {
            "alpha_issue": 1,
            "beta_issue": 1,
            "charlie_issue": 1,
        },
    )
    _write_lessons(
        tmp_path,
        "test-story",
        2,
        {
            "alpha_issue": 2,
            "charlie_issue": 1,
        },
    )
    _write_lessons(tmp_path, "test-story", 3, {"charlie_issue": 1})

    result = promote_findings("test-story", 3, stories_dir=tmp_path)

    assert result == {
        "written": True,
        "promoted": ["alpha_issue", "charlie_issue"],
    }


def test_return_promoted_list_is_sorted(tmp_path: Path) -> None:
    _story_dir(tmp_path)
    _write_lessons(
        tmp_path,
        "test-story",
        1,
        {
            "zeta_issue": 1,
            "alpha_issue": 1,
            "middle_issue": 1,
        },
    )
    _write_lessons(
        tmp_path,
        "test-story",
        2,
        {
            "middle_issue": 1,
            "zeta_issue": 1,
            "alpha_issue": 1,
        },
    )

    result = promote_findings("test-story", 2, stories_dir=tmp_path)

    assert result["promoted"] == ["alpha_issue", "middle_issue", "zeta_issue"]
