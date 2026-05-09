"""Tool for promoting chapter-level critique findings to wiki/style-notes.md."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src = str(Path(__file__).resolve().parents[1])
if _src not in sys.path:
    sys.path.insert(0, _src)

from tools._io import STORIES_DIR, _atomic_write, _validate_story_name  # noqa: E402
from tools._wiki import get_wiki_dir, parse_frontmatter, render_frontmatter  # noqa: E402

CHROMADB_DIR = os.environ.get("CHROMADB_DIR", str(PROJECT_ROOT / ".chromadb"))

_MIN_CHAPTERS = 2
_STYLE_NOTES_REQUIRED_FIELDS = ("type", "slug", "last_updated")


def _read_chapter_lessons(
    name: str,
    chapter_number: int,
    *,
    stories_dir: Path | None = None,
) -> dict[str, int]:
    """Read critique_lessons.json for a single chapter. Returns {} if not found."""
    base = stories_dir if stories_dir is not None else STORIES_DIR
    story_dir = _validate_story_name(name, base_dir=base)
    lessons_file = (
        story_dir / "chapters" / f"chapter_{chapter_number}" / "critique_lessons.json"
    )
    if not lessons_file.exists():
        return {}

    try:
        data = json.loads(lessons_file.read_text())
    except (json.JSONDecodeError, OSError):
        return {}

    if not isinstance(data, dict):
        return {}

    lessons: dict[str, int] = {}
    for criterion, count in data.items():
        if (
            isinstance(criterion, str)
            and isinstance(count, int)
            and not isinstance(count, bool)
        ):
            lessons[criterion] = count
    return lessons


def _aggregate_cross_chapter_findings(
    name: str,
    chapter_number: int,
    *,
    stories_dir: Path | None = None,
) -> dict[str, list[int]]:
    """Return {criterion: [chapter_numbers_that_flagged_it]} for chapters 1..N."""
    result: dict[str, list[int]] = {}
    for number in range(1, chapter_number + 1):
        lessons = _read_chapter_lessons(name, number, stories_dir=stories_dir)
        for criterion, count in lessons.items():
            if count > 0:
                result.setdefault(criterion, []).append(number)
    return result


def _build_style_notes_body(promoted: dict[str, list[int]], chapter_number: int) -> str:
    """Build markdown body for wiki/style-notes.md."""
    lines: list[str] = [
        "# Style Notes",
        "",
        "Recurring critique patterns promoted from chapter lessons. "
        "Injected into scene drafts via wiki context machinery.",
        "",
        f"*Last updated: chapter {chapter_number}*",
        "",
        "## Promoted Findings",
        "",
    ]
    for criterion in sorted(promoted):
        chapters = sorted(promoted[criterion])
        lines.append(f"### {criterion}")
        lines.append(f"Flagged in chapters: {', '.join(str(ch) for ch in chapters)}")
        lines.append(f"Total chapter occurrences: {len(chapters)}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _upsert_to_chromadb(
    story_name: str,
    page_path: Path,
    body: str,
    frontmatter: dict[str, Any],
) -> None:
    """Upsert style-notes.md to the wiki ChromaDB collection. Graceful on failure."""
    try:
        import chromadb  # type: ignore[import-not-found]

        from tools._chroma_sync import upsert_from_source  # noqa: E402

        client = chromadb.PersistentClient(path=CHROMADB_DIR)
        collection = client.get_or_create_collection(name=f"wiki-{story_name}")
        extra_meta: dict[str, str | int | float | bool] = {
            "type": str(frontmatter.get("type", "style_notes")),
            "slug": str(frontmatter.get("slug", "style-notes")),
        }
        upsert_from_source(
            collection,
            doc_id="style-notes",
            source_path=str(page_path.relative_to(PROJECT_ROOT)),
            extra_metadata=extra_meta,
            body=body,
        )
    except Exception as exc:  # noqa: BLE001
        print(
            f"Warning: ChromaDB upsert for style-notes failed (non-fatal): {exc}",
            file=sys.stderr,
        )


def promote_findings(
    name: str,
    chapter_number: int,
    *,
    stories_dir: Path | None = None,
) -> dict[str, Any]:
    """Promote recurring critique findings to wiki/style-notes.md."""
    base = stories_dir if stories_dir is not None else STORIES_DIR
    story_dir = _validate_story_name(name, base_dir=base)
    wiki_dir = get_wiki_dir(story_dir)
    style_notes_path = wiki_dir / "style-notes.md"

    existing_fm: dict[str, Any] = {}
    if style_notes_path.exists():
        existing_content = style_notes_path.read_text()
        existing_fm, _ = parse_frontmatter(existing_content)
        if existing_fm.get("pinned") is True:
            return {"written": False, "promoted": []}

    cross_chapter = _aggregate_cross_chapter_findings(
        story_dir.name,
        chapter_number,
        stories_dir=base,
    )
    promoted = {
        criterion: chapters
        for criterion, chapters in cross_chapter.items()
        if len(chapters) >= _MIN_CHAPTERS
    }

    if not promoted:
        return {"written": False, "promoted": []}

    now_ts = datetime.now(timezone.utc).isoformat()
    suppress = existing_fm.get("suppress", False) is True
    version = 1
    if existing_fm:
        version_value = existing_fm.get("version", 1)
        if isinstance(version_value, int) and not isinstance(version_value, bool):
            version = version_value + 1

    frontmatter: dict[str, Any] = {
        "type": "style_notes",
        "slug": "style-notes",
        "last_updated": now_ts,
        "version": version,
        "pinned": False,
        "suppress": suppress,
    }

    for field in _STYLE_NOTES_REQUIRED_FIELDS:
        if field not in frontmatter:
            raise ValueError(f"Missing required style notes frontmatter field: {field}")

    body = _build_style_notes_body(promoted, chapter_number)
    full_content = render_frontmatter(frontmatter, body) + "\n"

    wiki_dir.mkdir(parents=True, exist_ok=True)
    _atomic_write(style_notes_path, full_content)

    if not suppress:
        _upsert_to_chromadb(story_dir.name, style_notes_path, body, frontmatter)

    return {"written": True, "promoted": sorted(promoted.keys())}
