"""CLI tool for reading wiki pages and matching entities."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src = str(Path(__file__).resolve().parents[1])
if _src not in sys.path:
    sys.path.insert(0, _src)

from src.tools._io import _validate_story_name  # noqa: E402
from src.tools._wiki import (  # noqa: E402
    find_pages,
    get_wiki_dir,
    match_entities_in_text,
    parse_frontmatter,
    read_index,
)


def _extract_sentences(text: str, count: int) -> str:
    """Extract the first N sentences from text."""
    import re

    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(sentences[:count])


def cmd_read(args: argparse.Namespace) -> None:
    """Read wiki pages by slug, type, or glob pattern."""
    story_dir = _validate_story_name(args.name)
    wiki_dir = get_wiki_dir(story_dir)

    if not wiki_dir.exists():
        print(json.dumps({"status": "ok", "pages": []}))
        return

    pages = find_pages(
        wiki_dir,
        slug=args.slug,
        page_type=args.type,
        glob_pattern=args.glob,
    )

    detail_level = args.detail_level or "brief"
    results: list[dict] = []

    for page_path in pages:
        content = page_path.read_text()
        metadata, body = parse_frontmatter(content)

        # Determine slug from metadata or filename
        slug = metadata.get("slug", page_path.stem)
        page_type = metadata.get("type", "unknown")
        detail_levels = metadata.get("detail_levels", {})

        entry: dict = {
            "slug": slug,
            "type": page_type,
            "metadata": metadata,
        }

        if detail_level == "headline":
            entry["content"] = detail_levels.get(
                "L1", body.split("\n")[0] if body else ""
            )
        elif detail_level == "brief":
            entry["content"] = detail_levels.get("L2", _extract_sentences(body, 3))
        elif detail_level == "full":
            entry["content"] = body

        results.append(entry)

    print(json.dumps({"status": "ok", "pages": results}, indent=2))


def cmd_match_entities(args: argparse.Namespace) -> None:
    """Match entity names in provided text against the wiki index."""
    if not args.text:
        print("Error: --text is required for match-entities", file=sys.stderr)
        sys.exit(2)

    story_dir = _validate_story_name(args.name)
    wiki_dir = get_wiki_dir(story_dir)

    if not wiki_dir.exists():
        print(json.dumps({"status": "ok", "matches": []}))
        return

    index_entries = read_index(wiki_dir)
    matches = match_entities_in_text(args.text, index_entries)

    print(json.dumps({"status": "ok", "matches": matches}, indent=2))


def main() -> None:
    """Parse arguments and dispatch to the appropriate command."""
    parser = argparse.ArgumentParser(description="Wiki read tool")
    parser.add_argument(
        "--operation",
        required=True,
        choices=["read", "match-entities"],
        help="Operation to perform",
    )
    parser.add_argument("--name", required=True, help="Story name")
    parser.add_argument("--slug", help="Page slug to read")
    parser.add_argument("--type", help="Page type to filter by")
    parser.add_argument("--glob", help="Glob pattern for page matching")
    parser.add_argument(
        "--detail-level",
        choices=["headline", "brief", "full"],
        default="brief",
        help="Detail level for returned content",
    )
    parser.add_argument("--text", help="Text to match entities against")

    args = parser.parse_args()

    if args.operation == "read":
        cmd_read(args)
    elif args.operation == "match-entities":
        cmd_match_entities(args)


if __name__ == "__main__":
    main()
