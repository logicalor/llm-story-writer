"""CLI tool for managing story character sheets."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src_path = str(PROJECT_ROOT / "src")
_root_path = str(PROJECT_ROOT)
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)
if _root_path not in sys.path:
    sys.path.insert(0, _root_path)

from src.tools._io import STORIES_DIR, _atomic_write, _validate_story_name  # noqa: E402


def _load_prompt(prompt_id: str, variables: dict[str, Any] | None = None) -> str:
    """Load and render a prompt template."""
    from infrastructure.prompts.prompt_loader import PromptLoader

    loader = PromptLoader(prompts_dir=str(PROJECT_ROOT / "prompts"))
    return loader.load_prompt(prompt_id, variables)


def _call_llm(prompt: str, *, model: str | None = None) -> str:
    """Call LLM with a single prompt and return text response."""
    from src.tools._llm import generate_text

    return generate_text(prompt, model=model)


def _load_story_elements(story_name: str) -> str | None:
    """Load story_elements savepoint content if present."""
    from infrastructure.storage.savepoint_repository import (
        FilesystemSavepointRepository,
    )

    story_dir = _validate_story_name(story_name, base_dir=STORIES_DIR)
    repo = FilesystemSavepointRepository(base_path=story_dir)
    repo.set_story_directory("savepoints")
    if not asyncio.run(repo.has_savepoint("story_elements")):
        return None
    data = asyncio.run(repo.load_savepoint("story_elements"))
    return data if isinstance(data, str) else str(data)


def _slugify(character_name: str) -> str:
    """Convert character name to filesystem-safe slug."""
    slug = character_name.lower().replace(" ", "-")
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


def _validate_character_name(name: str, story_name: str) -> Path:
    """Validate character name does not escape the characters directory."""
    if ".." in name:
        print(
            f"Error: character name must not contain '..': {name}",
            file=sys.stderr,
        )
        sys.exit(1)
    slug = _slugify(name)
    if not slug:
        print(
            f"Error: character name produces empty slug: {name}",
            file=sys.stderr,
        )
        sys.exit(1)
    story_dir = _validate_story_name(story_name)
    characters_dir = (story_dir / "characters").resolve()
    char_path = (characters_dir / f"{slug}.json").resolve()
    if not char_path.is_relative_to(characters_dir):
        print(
            f"Error: character name escapes characters directory: {name}",
            file=sys.stderr,
        )
        sys.exit(1)
    return char_path


def cmd_extract_names(args: argparse.Namespace) -> None:
    """Extract character names from LLM output."""
    if args.data is None:
        print("Error: --data is required for extract-names", file=sys.stderr)
        sys.exit(2)
    _validate_story_name(args.name)

    try:
        parsed = json.loads(args.data)
    except json.JSONDecodeError:
        print("Error: --data is not valid JSON", file=sys.stderr)
        sys.exit(1)

    if isinstance(parsed, list):
        names = parsed
    elif isinstance(parsed, str):
        try:
            names = json.loads(parsed)
            if not isinstance(names, list):
                print("Error: expected JSON array of names", file=sys.stderr)
                sys.exit(1)
        except json.JSONDecodeError:
            print("Error: --data string does not contain a JSON array", file=sys.stderr)
            sys.exit(1)
    else:
        print("Error: expected JSON array of names", file=sys.stderr)
        sys.exit(1)

    if not all(isinstance(n, str) for n in names):
        print("Error: all names must be strings", file=sys.stderr)
        sys.exit(1)

    print(json.dumps({"names": names}, indent=2))


def cmd_generate_sheet(args: argparse.Namespace) -> None:
    """Generate and save a character sheet.

    Default mode: load prompt, call LLM, store result.
    Escape hatch: pass --data to skip generation and store provided content directly.
    """
    if not args.character:
        print("Error: --character is required for generate-sheet", file=sys.stderr)
        sys.exit(2)

    _validate_story_name(args.name)
    char_path = _validate_character_name(args.character, args.name)

    if args.data is not None:
        # Escape hatch: direct storage of caller-provided content
        try:
            data = json.loads(args.data)
        except json.JSONDecodeError:
            print("Error: --data is not valid JSON", file=sys.stderr)
            sys.exit(1)

        if not isinstance(data, dict):
            print("Error: --data must be a JSON object", file=sys.stderr)
            sys.exit(1)

        sheet_text = data.get("sheet", "")
        chunks = data.get("chunks", {})
        summary = data.get("summary", "")
    else:
        # Default: generate sheet via LLM
        story_elements = _load_story_elements(args.name)
        if story_elements is None:
            print(
                "Error: story_elements savepoint not found — run outline generation first, or pass --data",
                file=sys.stderr,
            )
            sys.exit(1)

        additional_context = args.additional_context or ""
        try:
            prompt_text = _load_prompt(
                "characters/create",
                {
                    "story_elements": story_elements,
                    "character_name": args.character,
                    "additional_context": additional_context,
                },
            )
        except Exception as exc:
            print(f"Error: failed to load prompt: {exc}", file=sys.stderr)
            sys.exit(1)

        try:
            sheet_text = _call_llm(prompt_text, model=args.model)
        except Exception as exc:
            print(f"Error: LLM call failed: {exc}", file=sys.stderr)
            sys.exit(1)

        if not sheet_text.strip():
            print("Error: LLM returned empty sheet content", file=sys.stderr)
            sys.exit(1)

        chunks = {}
        summary = ""

    sheet_data = {
        "name": args.character,
        "sheet": sheet_text,
        "chunks": chunks,
        "summary": summary,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    _atomic_write(char_path, json.dumps(sheet_data, indent=2))

    rel_path = str(char_path.relative_to(STORIES_DIR.resolve().parent))
    word_count = len(sheet_text.split())
    print(
        json.dumps(
            {"status": "ok", "path": rel_path, "word_count": word_count},
            indent=2,
        )
    )


def cmd_update_sheet(args: argparse.Namespace) -> None:
    """Update an existing character sheet with partial data."""
    if args.data is None:
        print("Error: --data is required for update-sheet", file=sys.stderr)
        sys.exit(2)
    if not args.character:
        print("Error: --character is required for update-sheet", file=sys.stderr)
        sys.exit(2)

    _validate_story_name(args.name)
    char_path = _validate_character_name(args.character, args.name)

    if not char_path.exists():
        print(f"Error: character sheet not found: {args.character}", file=sys.stderr)
        sys.exit(1)

    try:
        existing = json.loads(char_path.read_text())
    except json.JSONDecodeError:
        print(f"Error: corrupted character sheet: {args.character}", file=sys.stderr)
        sys.exit(1)

    try:
        updates = json.loads(args.data)
    except json.JSONDecodeError:
        print("Error: --data is not valid JSON", file=sys.stderr)
        sys.exit(1)

    if not isinstance(updates, dict):
        print("Error: --data must be a JSON object", file=sys.stderr)
        sys.exit(1)

    if "sheet" in updates:
        existing["sheet"] = updates["sheet"]
    if "summary" in updates:
        existing["summary"] = updates["summary"]
    if "chunks" in updates and isinstance(updates["chunks"], dict):
        if "chunks" not in existing or not isinstance(existing.get("chunks"), dict):
            existing["chunks"] = {}
        for key, value in updates["chunks"].items():
            existing["chunks"][key] = value

    existing["updated_at"] = datetime.now(timezone.utc).isoformat()

    _atomic_write(char_path, json.dumps(existing, indent=2))

    rel_path = str(char_path.relative_to(STORIES_DIR.resolve().parent))
    print(json.dumps({"status": "ok", "path": rel_path}, indent=2))


def cmd_load_sheet(args: argparse.Namespace) -> None:
    """Load a character sheet from disk."""
    if not args.character:
        print("Error: --character is required for load-sheet", file=sys.stderr)
        sys.exit(2)

    _validate_story_name(args.name)
    char_path = _validate_character_name(args.character, args.name)

    if not char_path.exists():
        print(f"Error: character sheet not found: {args.character}", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(char_path.read_text())
    except json.JSONDecodeError:
        print(f"Error: corrupted character sheet: {args.character}", file=sys.stderr)
        sys.exit(1)

    if args.abridged:
        data = {
            "name": data.get("name", ""),
            "summary": data.get("summary", ""),
            "updated_at": data.get("updated_at", ""),
        }

    print(json.dumps(data, indent=2))


def cmd_list(args: argparse.Namespace) -> None:
    """List all character sheets for a story."""
    story_dir = _validate_story_name(args.name)
    characters_dir = story_dir / "characters"

    if not characters_dir.exists():
        print(json.dumps({"characters": []}, indent=2))
        return

    names: list[str] = []
    for path in sorted(characters_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text())
            names.append(data.get("name", path.stem))
        except (json.JSONDecodeError, OSError):
            names.append(path.stem)

    print(json.dumps({"characters": names}, indent=2))


def cmd_generate_abridged(args: argparse.Namespace) -> None:
    """Generate an abridged summary from a character sheet."""
    if not args.character:
        print("Error: --character is required for generate-abridged", file=sys.stderr)
        sys.exit(2)

    _validate_story_name(args.name)
    char_path = _validate_character_name(args.character, args.name)

    if not char_path.exists():
        print(f"Error: character sheet not found: {args.character}", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(char_path.read_text())
    except json.JSONDecodeError:
        print(f"Error: corrupted character sheet: {args.character}", file=sys.stderr)
        sys.exit(1)

    sheet_text = data.get("sheet", "")
    budget = args.budget
    word_limit = int(budget * 0.75)

    words = sheet_text.split()
    truncated = " ".join(words[:word_limit])

    data["summary"] = truncated
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    _atomic_write(char_path, json.dumps(data, indent=2))

    rel_path = str(char_path.relative_to(STORIES_DIR.resolve().parent))
    print(json.dumps({"summary": truncated, "path": rel_path}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage story character sheets.")
    parser.add_argument(
        "--operation",
        required=True,
        choices=[
            "extract-names",
            "generate-sheet",
            "update-sheet",
            "load-sheet",
            "list",
            "generate-abridged",
        ],
        help="Operation to perform",
    )
    parser.add_argument("--name", required=True, help="Story name")
    parser.add_argument(
        "--character",
        default=None,
        help="Character name (required for most operations)",
    )
    parser.add_argument(
        "--data",
        default=None,
        help="JSON string input (required for extract-names, update-sheet; optional escape hatch for generate-sheet)",
    )
    parser.add_argument(
        "--additional-context",
        default=None,
        help="Extra context to inject into character generation prompt",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="LLM model name for generate-sheet (default: uses default model)",
    )
    parser.add_argument(
        "--budget",
        type=int,
        default=500,
        help="Word budget for generate-abridged (default: 500)",
    )
    parser.add_argument(
        "--abridged",
        action="store_true",
        help="Return abridged version for load-sheet",
    )
    args = parser.parse_args()

    op = args.operation
    if op == "extract-names":
        cmd_extract_names(args)
    elif op == "generate-sheet":
        cmd_generate_sheet(args)
    elif op == "update-sheet":
        cmd_update_sheet(args)
    elif op == "load-sheet":
        cmd_load_sheet(args)
    elif op == "list":
        cmd_list(args)
    elif op == "generate-abridged":
        cmd_generate_abridged(args)


if __name__ == "__main__":
    main()
