"""CLI tool for assembling saved chapter content into a single story markdown file."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any, NoReturn

PROJECT_ROOT = Path(__file__).resolve().parents[2]

_src_path = str(PROJECT_ROOT / "src")
_root_path = str(PROJECT_ROOT)
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)
if _root_path not in sys.path:
    sys.path.insert(0, _root_path)

from domain.exceptions import ConfigurationError  # noqa: E402
from infrastructure.prompts.prompt_loader import PromptLoader  # noqa: E402
from infrastructure.storage.savepoint_repository import (  # noqa: E402
    FilesystemSavepointRepository,
)
from src.tools._io import STORIES_DIR, _validate_story_name  # noqa: E402
from src.tools._llm import generate_text  # noqa: E402
from src.tools.story_state import _set_nested, _write_state_atomic  # noqa: E402

CHAPTER_SAVEPOINT_PATTERNS = (
    "chapter_{chapter_num}_complete",
    "chapter_{chapter_num}/complete",
    "chapter_{chapter_num}",
)


def _make_repo(name: str) -> FilesystemSavepointRepository:
    """Create a FilesystemSavepointRepository for the given story."""
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


def _load_prompt(prompt_id: str, variables: dict[str, Any] | None = None) -> str:
    """Load and render a prompt template."""
    loader = PromptLoader(prompts_dir=str(PROJECT_ROOT / "prompts"))
    return loader.load_prompt(prompt_id, variables)


def _call_llm(prompt: str, *, model: str | None = None) -> str:
    """Call LLM with a single prompt and return text response."""
    return generate_text(prompt, model=model)


def _strip_json_fences(text: str) -> str:
    """Strip markdown code fences from a JSON response."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove first and last fence lines.
        start = 1
        end = len(lines)
        for i in range(len(lines) - 1, 0, -1):
            if lines[i].strip() == "```":
                end = i
                break
        text = "\n".join(lines[start:end]).strip()
    return text


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

    try:
        asyncio.run(
            repo.save_savepoint(
                "story_complete",
                {
                    "status": "complete",
                    "chapter_count": len(chapter_parts),
                    "output_path": f"stories/{story_name}/output/story.md",
                },
            )
        )
    except Exception as exc:
        print(
            f"Warning: story_complete savepoint write failed: {exc}",
            file=sys.stderr,
        )

    print(
        json.dumps(
            {
                "output_path": f"stories/{story_name}/output/story.md",
                "chapter_count": len(chapter_parts),
            },
            indent=2,
        )
    )


def cmd_generate_handoff(
    story_name: str,
    chapter_num: int,
    model: str | None = None,
) -> None:
    """Generate a chapter handoff artifact and write it to story state."""
    story_dir = _validate_story_name(story_name)
    if not story_dir.exists():
        _error(f"story not found: {story_name}")
    if not story_dir.resolve().is_relative_to(STORIES_DIR.resolve()):
        _error(f"story path escapes stories dir: {story_name}")

    story_state = _load_story_state(story_dir)
    repo = _make_repo(story_name)

    chapters = story_state.get("chapters", {})
    chapter_data: dict[str, Any] = {}
    if isinstance(chapters, dict):
        candidate = chapters.get(str(chapter_num)) or chapters.get(chapter_num) or {}
        if isinstance(candidate, dict):
            chapter_data = candidate

    expanded_step = f"expanded_chapter_{chapter_num}_{chapter_num}"
    if _has_savepoint(repo, expanded_step):
        expanded_outline_raw = _load_savepoint(repo, expanded_step)
        expanded_outline = (
            expanded_outline_raw
            if isinstance(expanded_outline_raw, str)
            else json.dumps(expanded_outline_raw, default=str)
        )
    else:
        expanded_outline = chapter_data.get("expanded_outline", "")

    if not expanded_outline.strip():
        _error(
            f"no expanded outline found for chapter {chapter_num} — "
            f"run outline expansion (Phase 7a) first"
        )

    chapter_title = chapter_data.get("title", f"Chapter {chapter_num}")
    story_context = story_state.get("story_context", {})
    story_title = story_context.get("title", "")

    try:
        prompt = _load_prompt(
            "chapters/generate_handoff",
            {
                "CHAPTER_NUMBER": str(chapter_num),
                "CHAPTER_OUTLINE": expanded_outline,
                "CHAPTER_TITLE": chapter_title,
                "STORY_TITLE": story_title,
            },
        )
    except ConfigurationError:
        _error("prompt not found: chapters/generate_handoff")

    raw_response = _call_llm(prompt, model=model)
    cleaned = _strip_json_fences(raw_response)

    try:
        handoff = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        _error(f"LLM returned invalid JSON for handoff: {exc}")

    state_path = story_dir / "state.json"
    _set_nested(story_state, f"chapters.{chapter_num}.handoff", handoff)
    _write_state_atomic(state_path, story_state)

    print(
        json.dumps(
            {
                "status": "success",
                "chapter_num": chapter_num,
                "handoff_keys": list(handoff.keys())
                if isinstance(handoff, dict)
                else [],
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

    generate_handoff_parser = subparsers.add_parser(
        "generate-handoff", help="Generate chapter handoff artifact"
    )
    generate_handoff_parser.add_argument(
        "--story-name",
        required=True,
        help="Story name (directory under stories/)",
    )
    generate_handoff_parser.add_argument(
        "--chapter-num",
        required=True,
        type=int,
        help="Chapter number to generate handoff for",
    )
    generate_handoff_parser.add_argument(
        "--model",
        default=None,
        help="Model override (optional)",
    )

    args = parser.parse_args()

    if args.command == "assemble":
        cmd_assemble(args.story_name)
        return

    if args.command == "generate-handoff":
        cmd_generate_handoff(args.story_name, args.chapter_num, args.model)
        return

    parser.print_help()
    sys.exit(2)


if __name__ == "__main__":
    main()
