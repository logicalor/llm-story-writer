"""CLI tool for assembling saved chapter content into a single story markdown file."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, NoReturn

if TYPE_CHECKING:
    from infrastructure.storage.savepoint_repository import FilesystemSavepointRepository

PROJECT_ROOT = Path(__file__).resolve().parents[2]

_src_path = str(PROJECT_ROOT / "src")
_root_path = str(PROJECT_ROOT)
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)
if _root_path not in sys.path:
    sys.path.insert(0, _root_path)

from src.tools._io import _validate_story_name  # noqa: E402

CHAPTER_SAVEPOINT_PATTERNS = (
    "chapter_{chapter_num}_complete",
    "chapter_{chapter_num}/complete",
    "chapter_{chapter_num}",
)


def _make_repo(name: str) -> FilesystemSavepointRepository:
    """Create a FilesystemSavepointRepository for the given story."""
    from infrastructure.storage.savepoint_repository import FilesystemSavepointRepository

    story_dir = _validate_story_name(name)
    repo = FilesystemSavepointRepository(base_path=story_dir)
    repo.set_story_directory("savepoints")
    return repo


def _load_savepoint(repo: FilesystemSavepointRepository, step: str) -> Any:
    """Load a savepoint, returning its data."""
    return asyncio.run(repo.load_savepoint(step))


def _has_savepoint(repo: FilesystemSavepointRepository, step: str) -> bool:
    """Check if a savepoint exists."""
    return asyncio.run(repo.has_savepoint(step))


def _list_savepoint_names(repo: FilesystemSavepointRepository) -> list[str]:
    """List available savepoint names for the story."""
    return asyncio.run(repo.list_savepoint_names())


def _error(message: str, exit_code: int = 1) -> NoReturn:
    """Print error to stderr and exit."""
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(exit_code)


def _normalize_state(data: Any) -> dict[str, Any]:
    """Validate story state payload shape."""
    if not isinstance(data, dict):
        return {}
    return data


def _load_story_state(story_dir: Path) -> dict[str, Any]:
    """Load story state from disk if available."""
    state_path = story_dir / "state.json"
    if not state_path.exists():
        return {}
    try:
        return _normalize_state(json.loads(state_path.read_text(encoding="utf-8")))
    except json.JSONDecodeError as exc:
        _error(f"invalid state.json for story: {exc}")


def _extract_state_chapter_text(chapters: Any, chapter_num: int) -> str | None:
    """Extract chapter text from story state using common field names."""
    chapter_data: Any = None

    if isinstance(chapters, dict):
        chapter_data = chapters.get(str(chapter_num), chapters.get(chapter_num))
    elif isinstance(chapters, list):
        for entry in chapters:
            if not isinstance(entry, dict):
                continue
            number = entry.get("number")
            if isinstance(number, int) and number == chapter_num:
                chapter_data = entry
                break

    if isinstance(chapter_data, str):
        return chapter_data
    if not isinstance(chapter_data, dict):
        return None

    for key in ("content", "text", "chapter_text", "assembled"):
        value = chapter_data.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _load_chapter_content(
    repo: FilesystemSavepointRepository,
    story_state: dict[str, Any],
    chapter_num: int,
) -> str | None:
    """Load chapter content from savepoints, falling back to story state."""
    for pattern in CHAPTER_SAVEPOINT_PATTERNS:
        step = pattern.format(chapter_num=chapter_num)
        if _has_savepoint(repo, step):
            data = _load_savepoint(repo, step)
            if isinstance(data, str) and data.strip():
                return data
            if data is not None:
                return json.dumps(data, indent=2, default=str)

    return _extract_state_chapter_text(story_state.get("chapters", {}), chapter_num)


def _discover_chapter_numbers(
    repo: FilesystemSavepointRepository,
    story_state: dict[str, Any],
) -> list[int]:
    """Determine chapter numbers from savepoints and story state."""
    numbers: set[int] = set()

    chapter_pattern = re.compile(r"^chapter_(\d+)(?:_complete|/complete)?$")
    for step_name in _list_savepoint_names(repo):
        match = chapter_pattern.match(step_name)
        if match:
            numbers.add(int(match.group(1)))

    chapters = story_state.get("chapters", {})
    if isinstance(chapters, dict):
        for key in chapters:
            if isinstance(key, int):
                numbers.add(key)
            elif isinstance(key, str) and key.isdigit():
                numbers.add(int(key))
    elif isinstance(chapters, list):
        for entry in chapters:
            if isinstance(entry, dict):
                number = entry.get("number")
                if isinstance(number, int):
                    numbers.add(number)

    return sorted(numbers)


def cmd_assemble(story_name: str) -> None:
    """Assemble all available chapter content into a single story markdown file."""
    story_dir = _validate_story_name(story_name)
    if not story_dir.exists():
        _error(f"story not found: {story_name}")

    repo = _make_repo(story_name)
    story_state = _load_story_state(story_dir)

    chapter_numbers = _discover_chapter_numbers(repo, story_state)
    if not chapter_numbers:
        _error("no chapter content found in savepoints or story state")

    chapter_parts: list[str] = []
    for chapter_num in chapter_numbers:
        chapter_content = _load_chapter_content(repo, story_state, chapter_num)
        if not chapter_content:
            continue
        chapter_parts.append(chapter_content.rstrip())

    if not chapter_parts:
        _error("no readable chapter content found in savepoints or story state")

    output_path = story_dir / "output" / "story.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n\n".join(chapter_parts) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "output_path": f"stories/{story_name}/output/story.md",
                "chapter_count": len(chapter_parts),
            },
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Assemble completed chapter content")
    subparsers = parser.add_subparsers(dest="command")

    assemble_parser = subparsers.add_parser("assemble", help="Assemble story output")
    assemble_parser.add_argument(
        "--story-name",
        required=True,
        help="Story name (directory under stories/)",
    )

    args = parser.parse_args()

    if args.command == "assemble":
        cmd_assemble(args.story_name)
        return

    parser.print_help()
    sys.exit(2)


if __name__ == "__main__":
    main()