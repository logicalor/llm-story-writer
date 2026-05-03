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
from tools._persist import persist_markdown, read_markdown_ref  # noqa: E402


def _load_prompt(prompt_id: str, variables: dict[str, Any] | None = None) -> str:
    """Load and render a prompt template."""
    from infrastructure.prompts.prompt_loader import PromptLoader

    loader = PromptLoader(prompts_dir=str(PROJECT_ROOT / "prompts"))
    return loader.load_prompt(prompt_id, variables)


def _call_llm(prompt: str, *, model: str | None = None) -> str:
    """Call LLM with a single prompt and return text response."""
    from src.tools._llm import generate_text

    return generate_text(prompt, model=model)


def _extract_output_content(text: str) -> str:
    """Extract content between <output>...</output> tags, or return text stripped."""
    match = re.search(r"<output>(.*?)</output>", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


CHUNK_PROMPT_MAP: dict[str, str] = {
    "backstory": "characters/create_background_chunk",
    "personality": "characters/create_personality_chunk",
    "motivation": "characters/create_motivations_chunk",
    "relationships": "characters/create_relationships_chunk",
    "skills": "characters/create_skills_chunk",
    "arc": "characters/create_growth_arc_chunk",
    "current_state": "characters/create_current_state_chunk",
}


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
    story_root = char_path.parent.parent
    slug = char_path.stem

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
        abridged = data.get("abridged", "")
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
        abridged = ""

    sheet_data = {
        "name": args.character,
        "sheet": persist_markdown(
            story_root, f"characters/{slug}/sheet.md", sheet_text
        ),
        "chunks": {
            k: persist_markdown(story_root, f"characters/{slug}/chunks/{k}.md", v)
            for k, v in chunks.items()
        },
        "summary": persist_markdown(
            story_root, f"characters/{slug}/summary.md", summary
        ),
        "abridged": persist_markdown(
            story_root, f"characters/{slug}/abridged.md", abridged
        ),
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
    story_root = char_path.parent.parent
    slug = char_path.stem

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
        existing["sheet"] = persist_markdown(
            story_root, f"characters/{slug}/sheet.md", updates["sheet"]
        )
    if "summary" in updates:
        existing["summary"] = persist_markdown(
            story_root, f"characters/{slug}/summary.md", updates["summary"]
        )
    if "abridged" in updates:
        existing["abridged"] = persist_markdown(
            story_root, f"characters/{slug}/abridged.md", updates["abridged"]
        )
    if "chunks" in updates and isinstance(updates["chunks"], dict):
        if "chunks" not in existing or not isinstance(existing.get("chunks"), dict):
            existing["chunks"] = {}
        for key, value in updates["chunks"].items():
            existing["chunks"][key] = persist_markdown(
                story_root, f"characters/{slug}/chunks/{key}.md", value
            )

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

    story_root = char_path.parent.parent
    data["sheet"] = (
        read_markdown_ref(story_root, _ref)
        if isinstance(_ref := data.get("sheet"), dict)
        else (_ref or "")
    )
    data["chunks"] = {
        k: (read_markdown_ref(story_root, v) if isinstance(v, dict) else (v or ""))
        for k, v in data.get("chunks", {}).items()
    }
    data["summary"] = (
        read_markdown_ref(story_root, _ref)
        if isinstance(_ref := data.get("summary"), dict)
        else (_ref or "")
    )
    data["abridged"] = (
        read_markdown_ref(story_root, _ref)
        if isinstance(_ref := data.get("abridged"), dict)
        else (_ref or "")
    )

    if args.abridged:
        data = {
            "name": data.get("name", ""),
            "abridged": data.get("abridged", ""),
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


def cmd_generate_chunks(args: argparse.Namespace) -> None:
    """Generate semantic chunks from an existing character sheet."""
    if not args.character:
        print("Error: --character is required for generate-chunks", file=sys.stderr)
        sys.exit(2)

    _validate_story_name(args.name)
    char_path = _validate_character_name(args.character, args.name)
    story_root = char_path.parent.parent
    slug = char_path.stem

    if not char_path.exists():
        print(f"Error: character sheet not found: {args.character}", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(char_path.read_text())
    except json.JSONDecodeError:
        print(f"Error: corrupted character sheet: {args.character}", file=sys.stderr)
        sys.exit(1)

    sheet_text = (
        read_markdown_ref(story_root, _ref)
        if isinstance(_ref := data.get("sheet"), dict)
        else (_ref or "")
    )
    if not sheet_text.strip():
        print(
            "Error: character sheet is empty — run generate-sheet first",
            file=sys.stderr,
        )
        sys.exit(1)

    story_elements = _load_story_elements(args.name) or ""

    chunk_map = CHUNK_PROMPT_MAP
    if args.chunk:
        if args.chunk not in chunk_map:
            valid = ", ".join(chunk_map.keys())
            print(
                f"Error: unknown chunk type '{args.chunk}'. Valid: {valid}",
                file=sys.stderr,
            )
            sys.exit(1)
        chunk_map = {args.chunk: chunk_map[args.chunk]}

    chunks: dict[str, str] = data.get("chunks", {})
    generated: list[str] = []

    for chunk_key, prompt_id in chunk_map.items():
        try:
            prompt_text = _load_prompt(
                prompt_id,
                {
                    "character_name": args.character,
                    "character_sheet": sheet_text,
                    "story_elements": story_elements,
                },
            )
        except Exception as exc:
            print(
                f"Error: failed to load prompt for '{chunk_key}': {exc}",
                file=sys.stderr,
            )
            sys.exit(1)

        try:
            result = _call_llm(prompt_text, model=args.model)
        except Exception as exc:
            print(f"Error: LLM call failed for '{chunk_key}': {exc}", file=sys.stderr)
            sys.exit(1)

        chunk_text = _extract_output_content(result)
        chunks[chunk_key] = persist_markdown(
            story_root, f"characters/{slug}/chunks/{chunk_key}.md", chunk_text
        )
        generated.append(chunk_key)

    data["chunks"] = chunks
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    _atomic_write(char_path, json.dumps(data, indent=2))

    rel_path = str(char_path.relative_to(STORIES_DIR.resolve().parent))
    print(
        json.dumps(
            {"status": "ok", "path": rel_path, "chunks_generated": generated}, indent=2
        )
    )


def cmd_generate_summary(args: argparse.Namespace) -> None:
    """Generate a natural language summary from existing chunks."""
    if not args.character:
        print("Error: --character is required for generate-summary", file=sys.stderr)
        sys.exit(2)

    _validate_story_name(args.name)
    char_path = _validate_character_name(args.character, args.name)
    story_root = char_path.parent.parent
    slug = char_path.stem

    if not char_path.exists():
        print(f"Error: character sheet not found: {args.character}", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(char_path.read_text())
    except json.JSONDecodeError:
        print(f"Error: corrupted character sheet: {args.character}", file=sys.stderr)
        sys.exit(1)

    chunks_raw: dict = data.get("chunks", {})
    chunks = {
        k: (read_markdown_ref(story_root, v) if isinstance(v, dict) else (v or ""))
        for k, v in chunks_raw.items()
    }
    valid_chunks = {
        k: v
        for k, v in chunks.items()
        if v and not v.lower().startswith("please provide")
    }
    if not valid_chunks:
        print(
            "Error: no valid chunks found — run generate-chunks first", file=sys.stderr
        )
        sys.exit(1)

    character_info = "\n\n".join(
        f"=== {key.replace('_', ' ').title()} ===\n{value}"
        for key, value in valid_chunks.items()
    )

    try:
        prompt_text = _load_prompt(
            "characters/create_summary",
            {
                "character_name": args.character,
                "character_info": character_info,
            },
        )
    except Exception as exc:
        print(f"Error: failed to load prompt: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        summary = _call_llm(prompt_text, model=args.model)
    except Exception as exc:
        print(f"Error: LLM call failed: {exc}", file=sys.stderr)
        sys.exit(1)

    data["summary"] = persist_markdown(
        story_root,
        f"characters/{slug}/summary.md",
        _extract_output_content(summary),
    )
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    _atomic_write(char_path, json.dumps(data, indent=2))

    rel_path = str(char_path.relative_to(STORIES_DIR.resolve().parent))
    print(json.dumps({"status": "ok", "path": rel_path}, indent=2))


def cmd_generate_abridged(args: argparse.Namespace) -> None:
    """Generate a compact abridged summary via LLM using story_elements."""
    if not args.character:
        print("Error: --character is required for generate-abridged", file=sys.stderr)
        sys.exit(2)

    _validate_story_name(args.name)
    char_path = _validate_character_name(args.character, args.name)
    story_root = char_path.parent.parent
    slug = char_path.stem

    if not char_path.exists():
        print(f"Error: character sheet not found: {args.character}", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(char_path.read_text())
    except json.JSONDecodeError:
        print(f"Error: corrupted character sheet: {args.character}", file=sys.stderr)
        sys.exit(1)

    if args.data is not None:
        # Escape hatch: store caller-provided content directly to abridged
        data["abridged"] = persist_markdown(
            story_root, f"characters/{slug}/abridged.md", args.data
        )
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        _atomic_write(char_path, json.dumps(data, indent=2))
        rel_path = str(char_path.relative_to(STORIES_DIR.resolve().parent))
        print(json.dumps({"status": "ok", "path": rel_path}, indent=2))
        return

    story_elements = _load_story_elements(args.name)
    if story_elements is None:
        print(
            "Error: story_elements savepoint not found — run outline generation first, or pass --data",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        prompt_text = _load_prompt(
            "characters/create_abridged",
            {
                "character_name": args.character,
                "story_elements": story_elements,
            },
        )
    except Exception as exc:
        print(f"Error: failed to load prompt: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        abridged = _call_llm(prompt_text, model=args.model)
    except Exception as exc:
        print(f"Error: LLM call failed: {exc}", file=sys.stderr)
        sys.exit(1)

    data["abridged"] = persist_markdown(
        story_root,
        f"characters/{slug}/abridged.md",
        _extract_output_content(abridged),
    )
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    _atomic_write(char_path, json.dumps(data, indent=2))

    rel_path = str(char_path.relative_to(STORIES_DIR.resolve().parent))
    print(json.dumps({"status": "ok", "path": rel_path}, indent=2))


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
            "generate-chunks",
            "generate-summary",
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
        help="JSON string input (required for extract-names, update-sheet; optional escape hatch for generate-sheet and generate-abridged)",
    )
    parser.add_argument(
        "--additional-context",
        default=None,
        help="Extra context to inject into character generation prompt",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="LLM model name (default: uses default model)",
    )
    parser.add_argument(
        "--chunk",
        default=None,
        choices=list(CHUNK_PROMPT_MAP.keys()),
        help="Generate a single named chunk (generate-chunks only); omit to generate all",
    )
    parser.add_argument(
        "--budget",
        type=int,
        default=500,
        help="Deprecated — kept for backward compatibility, no longer used",
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
    elif op == "generate-chunks":
        cmd_generate_chunks(args)
    elif op == "generate-summary":
        cmd_generate_summary(args)
    elif op == "generate-abridged":
        cmd_generate_abridged(args)


if __name__ == "__main__":
    main()
