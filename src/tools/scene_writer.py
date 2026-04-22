"""CLI tool for scene writing pipeline (parse-definitions, generate, revise, assemble-chapter)."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, NoReturn

if TYPE_CHECKING:
    from infrastructure.storage.savepoint_repository import (
        FilesystemSavepointRepository,
    )

PROJECT_ROOT = Path(__file__).resolve().parents[2]

_src_path = str(PROJECT_ROOT / "src")
_root_path = str(PROJECT_ROOT)
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)
if _root_path not in sys.path:
    sys.path.insert(0, _root_path)

from src.tools._io import STORIES_DIR, _validate_story_name  # noqa: E402


def _make_repo(name: str) -> FilesystemSavepointRepository:
    """Create a FilesystemSavepointRepository for the given story."""
    from infrastructure.storage.savepoint_repository import (
        FilesystemSavepointRepository,
    )

    story_dir = _validate_story_name(name)
    repo = FilesystemSavepointRepository(base_path=story_dir)
    repo.set_story_directory("savepoints")
    return repo


def _load_savepoint(repo: FilesystemSavepointRepository, step: str) -> Any:
    """Load a savepoint, returning its data."""
    return asyncio.run(repo.load_savepoint(step))


def _save_savepoint(repo: FilesystemSavepointRepository, step: str, data: Any) -> None:
    """Save data to a savepoint."""
    asyncio.run(repo.save_savepoint(step, data))


def _has_savepoint(repo: FilesystemSavepointRepository, step: str) -> bool:
    """Check if a savepoint exists."""
    return asyncio.run(repo.has_savepoint(step))


def _load_prompt(prompt_id: str, variables: dict[str, Any] | None = None) -> str:
    """Load and render a prompt template."""
    from infrastructure.prompts.prompt_loader import PromptLoader

    loader = PromptLoader(prompts_dir=str(PROJECT_ROOT / "prompts"))
    return loader.load_prompt(prompt_id, variables)


def _call_llm(prompt: str, *, model: str | None = None) -> str:
    """Call LLM with a single prompt and return text response."""
    from src.tools._llm import generate_text

    return generate_text(prompt, model=model)


def _success(operation: str, data: Any) -> None:
    """Print success response and exit."""
    print(
        json.dumps(
            {"status": "success", "operation": operation, "data": data},
            indent=2,
            default=str,
        )
    )


def _error(message: str, exit_code: int = 1) -> NoReturn:
    """Print error to stderr and exit."""
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(exit_code)


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------


def cmd_parse_definitions(
    name: str,
    chapter_num: int,
    chapter_outline: str,
    *,
    model: str | None = None,
) -> None:
    """Parse a chapter outline into individual scene definitions."""
    _validate_story_name(name)
    repo = _make_repo(name)
    step = f"chapter_{chapter_num}/scene_definitions"

    if _has_savepoint(repo, step):
        definitions = _load_savepoint(repo, step)
        _success("parse-definitions", definitions)
        return

    prompt_text = _load_prompt(
        "scenes/parse_definitions", {"chapter_outline": chapter_outline}
    )

    try:
        from src.tools._llm import _extract_json_block

        raw = _call_llm(prompt_text, model=model)
        json_str = _extract_json_block(raw)
        definitions = json.loads(json_str)
    except (json.JSONDecodeError, RuntimeError) as exc:
        print(
            f"Warning: scene parse failed ({exc}), falling back to single scene",
            file=sys.stderr,
        )
        definitions = [
            {"title": f"Chapter {chapter_num} Scene", "description": chapter_outline}
        ]

    if not isinstance(definitions, list) or not all(
        isinstance(d, dict) for d in definitions
    ):
        print(
            "Warning: invalid definitions structure, falling back to single scene",
            file=sys.stderr,
        )
        definitions = [
            {"title": f"Chapter {chapter_num} Scene", "description": chapter_outline}
        ]

    _save_savepoint(repo, step, definitions)
    _success("parse-definitions", definitions)


def cmd_generate(
    name: str,
    chapter_num: int,
    scene_num: int,
    scene_definition: str,
    chapter_outline: str,
    *,
    base_context: str | None = None,
    story_elements: str | None = None,
    character_sheets: str | None = None,
    setting_sheets: str | None = None,
    previous_recap: str | None = None,
    previous_scene: str | None = None,
    next_scene_definition: str | None = None,
    next_chapter_synopsis: str | None = None,
    model: str | None = None,
) -> None:
    """Generate content for a single scene."""
    _validate_story_name(name)
    repo = _make_repo(name)
    step = f"chapter_{chapter_num}/scene_{scene_num}"

    if _has_savepoint(repo, step):
        content = _load_savepoint(repo, step)
        _success("generate", content)
        return

    prompt_text = _load_prompt(
        "scenes/create_content",
        {
            "chapter_num": str(chapter_num),
            "scene_num": str(scene_num),
            "scene_definition": scene_definition,
            "chapter_outline": chapter_outline,
            "base_context": base_context or "",
            "story_elements": story_elements or "",
            "character_sheets": character_sheets or "",
            "setting_sheets": setting_sheets or "",
            "previous_recap": previous_recap or "",
            "previous_scene": previous_scene or "",
            "next_scene_definition": next_scene_definition or "",
            "next_chapter_synopsis": next_chapter_synopsis or "",
        },
    )

    try:
        content = _call_llm(prompt_text, model=model)
    except RuntimeError as exc:
        _error(f"scene generation failed: {exc}")

    _save_savepoint(repo, step, content)
    _success("generate", content)


def cmd_revise(
    name: str,
    chapter_num: int,
    scene_num: int,
    scene_content: str,
    feedback: str,
    *,
    scene_definition: str | None = None,
    chapter_outline: str | None = None,
    model: str | None = None,
) -> None:
    """Revise scene content based on feedback."""
    _validate_story_name(name)
    repo = _make_repo(name)
    step = f"chapter_{chapter_num}/scene_{scene_num}"

    prompt_text = _load_prompt(
        "scenes/revise_content",
        {
            "scene_content": scene_content,
            "feedback": feedback,
            "scene_definition": scene_definition or "",
            "chapter_outline": chapter_outline or "",
        },
    )

    try:
        revised = _call_llm(prompt_text, model=model)
    except RuntimeError as exc:
        _error(f"scene revision failed: {exc}")

    _save_savepoint(repo, step, revised)
    _success("revise", revised)


def cmd_assemble_chapter(
    name: str,
    chapter_num: int,
    scene_count: int,
    *,
    chapter_title: str | None = None,
) -> None:
    """Assemble all scenes into a single chapter."""
    _validate_story_name(name)
    repo = _make_repo(name)

    title = chapter_title or f"Chapter {chapter_num}"
    missing: list[int] = []

    for i in range(1, scene_count + 1):
        step = f"chapter_{chapter_num}/scene_{i}"
        if not _has_savepoint(repo, step):
            missing.append(i)

    if missing:
        _error(f"missing scenes: {missing}")

    # Load scene definitions once for title lookup
    defs_step = f"chapter_{chapter_num}/scene_definitions"
    defs: list[Any] | None = None
    if _has_savepoint(repo, defs_step):
        loaded = _load_savepoint(repo, defs_step)
        if isinstance(loaded, list):
            defs = loaded

    parts: list[str] = []
    for i in range(1, scene_count + 1):
        step = f"chapter_{chapter_num}/scene_{i}"
        content = _load_savepoint(repo, step)
        if not isinstance(content, str):
            content = json.dumps(content, default=str)

        # Try to get scene title from definitions
        scene_title = f"Scene {i}"
        if defs is not None and len(defs) >= i:
            entry = defs[i - 1]
            if isinstance(entry, dict) and "title" in entry:
                scene_title = entry["title"]

        parts.append(f"## {scene_title}\n\n{content}")

    assembled = f"# {title}\n\n" + "\n\n---\n\n".join(parts)
    _success("assemble-chapter", assembled)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Scene writer tool")
    parser.add_argument(
        "--operation",
        required=True,
        choices=["parse-definitions", "generate", "revise", "assemble-chapter"],
        help="Operation to perform",
    )
    parser.add_argument("--name", required=True, help="Story name")
    parser.add_argument("--chapter-num", type=int, default=None, help="Chapter number")
    parser.add_argument("--scene-num", type=int, default=None, help="Scene number")
    parser.add_argument(
        "--scene-count", type=int, default=None, help="Total scenes in chapter"
    )
    parser.add_argument("--chapter-outline", default=None, help="Chapter outline text")
    parser.add_argument(
        "--scene-definition", default=None, help="Scene definition JSON"
    )
    parser.add_argument("--scene-content", default=None, help="Current scene content")
    parser.add_argument("--feedback", default=None, help="Revision feedback")
    parser.add_argument("--chapter-title", default=None, help="Chapter title")
    parser.add_argument("--base-context", default=None, help="Base story context")
    parser.add_argument("--story-elements", default=None, help="Story elements text")
    parser.add_argument("--character-sheets", default=None, help="Character sheets")
    parser.add_argument("--setting-sheets", default=None, help="Setting sheets")
    parser.add_argument("--previous-recap", default=None, help="Previous chapter recap")
    parser.add_argument("--previous-scene", default=None, help="Previous scene content")
    parser.add_argument(
        "--next-scene-definition", default=None, help="Next scene definition"
    )
    parser.add_argument(
        "--next-chapter-synopsis", default=None, help="Next chapter synopsis"
    )
    parser.add_argument("--model", default=None, help="Override LLM model identifier")
    args = parser.parse_args()

    # --- Dispatch ---
    op = args.operation

    if op == "parse-definitions":
        if args.chapter_num is None:
            _error("--chapter-num is required for parse-definitions")
        if args.chapter_num < 1:
            _error("--chapter-num must be >= 1")
        if not args.chapter_outline:
            _error("--chapter-outline is required for parse-definitions")
        cmd_parse_definitions(
            args.name,
            args.chapter_num,
            args.chapter_outline,
            model=args.model,
        )

    elif op == "generate":
        if args.chapter_num is None:
            _error("--chapter-num is required for generate")
        if args.chapter_num < 1:
            _error("--chapter-num must be >= 1")
        if args.scene_num is None:
            _error("--scene-num is required for generate")
        if args.scene_num < 1:
            _error("--scene-num must be >= 1")
        if not args.scene_definition:
            _error("--scene-definition is required for generate")
        if not args.chapter_outline:
            _error("--chapter-outline is required for generate")
        cmd_generate(
            args.name,
            args.chapter_num,
            args.scene_num,
            args.scene_definition,
            args.chapter_outline,
            base_context=args.base_context,
            story_elements=args.story_elements,
            character_sheets=args.character_sheets,
            setting_sheets=args.setting_sheets,
            previous_recap=args.previous_recap,
            previous_scene=args.previous_scene,
            next_scene_definition=args.next_scene_definition,
            next_chapter_synopsis=args.next_chapter_synopsis,
            model=args.model,
        )

    elif op == "revise":
        if args.chapter_num is None:
            _error("--chapter-num is required for revise")
        if args.chapter_num < 1:
            _error("--chapter-num must be >= 1")
        if args.scene_num is None:
            _error("--scene-num is required for revise")
        if args.scene_num < 1:
            _error("--scene-num must be >= 1")
        if not args.scene_content:
            _error("--scene-content is required for revise")
        if not args.feedback:
            _error("--feedback is required for revise")
        cmd_revise(
            args.name,
            args.chapter_num,
            args.scene_num,
            args.scene_content,
            args.feedback,
            scene_definition=args.scene_definition,
            chapter_outline=args.chapter_outline,
            model=args.model,
        )

    elif op == "assemble-chapter":
        if args.chapter_num is None:
            _error("--chapter-num is required for assemble-chapter")
        if args.chapter_num < 1:
            _error("--chapter-num must be >= 1")
        if args.scene_count is None:
            _error("--scene-count is required for assemble-chapter")
        if args.scene_count < 1:
            _error("--scene-count must be >= 1")
        cmd_assemble_chapter(
            args.name,
            args.chapter_num,
            args.scene_count,
            chapter_title=args.chapter_title,
        )


if __name__ == "__main__":
    main()
