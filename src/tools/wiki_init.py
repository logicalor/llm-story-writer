"""CLI tool for initialising a story wiki directory."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src = str(Path(__file__).resolve().parents[1])
if _src not in sys.path:
    sys.path.insert(0, _src)

from tools._io import _atomic_write, _validate_story_name  # noqa: E402
from tools._wiki import WIKI_SUBDIRS  # noqa: E402

SCHEMA_TEMPLATE = Path(__file__).resolve().parent / "wiki_schema_template.md"


def _init_wiki_for_story(story_name: str, base_dir: Path | None = None) -> dict:
    """Initialise wiki directory structure for a story.

    Returns a dict with status information.  Does NOT call sys.exit.
    """
    story_dir = _validate_story_name(story_name, base_dir)

    if not story_dir.exists():
        return {"error": "story directory not found", "story_name": story_name}

    wiki_dir = story_dir / "wiki"

    # Idempotent: if wiki already exists, report and return
    if wiki_dir.exists():
        return {
            "status": "ok",
            "wiki_dir": str(wiki_dir),
            "created": False,
            "already_exists": True,
        }

    # Create wiki root and subdirectories
    wiki_dir.mkdir(parents=True, exist_ok=True)
    for subdir in WIKI_SUBDIRS:
        (wiki_dir / subdir).mkdir(parents=True, exist_ok=True)

    # Copy schema template
    if SCHEMA_TEMPLATE.exists():
        shutil.copy2(str(SCHEMA_TEMPLATE), str(wiki_dir / "_schema.md"))
    else:
        print(
            "Warning: schema template not found, skipping _schema.md",
            file=sys.stderr,
        )

    # Create empty index.md
    _atomic_write(
        wiki_dir / "index.md",
        "# Wiki Index\n\n<!-- slug | type | name | aliases | path -->\n",
    )

    # Create empty log.md
    _atomic_write(wiki_dir / "log.md", "# Wiki Change Log\n")

    # Create empty contradictions.md
    _atomic_write(wiki_dir / "contradictions.md", "# Contradictions Log\n")

    return {
        "status": "ok",
        "wiki_dir": str(wiki_dir),
        "created": True,
    }


def cmd_init(args: argparse.Namespace) -> None:
    """CLI entry point: initialise wiki directory structure for a story."""
    result = _init_wiki_for_story(args.name)

    if "error" in result:
        print(f"Error: {result['error']}: {result['story_name']}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(result))


def main() -> None:
    """Parse arguments and dispatch to the init command."""
    parser = argparse.ArgumentParser(description="Wiki init tool")
    parser.add_argument(
        "--operation",
        required=True,
        choices=["init"],
        help="Operation to perform",
    )
    parser.add_argument("--name", required=True, help="Story name")

    args = parser.parse_args()

    if args.operation == "init":
        cmd_init(args)


if __name__ == "__main__":
    main()
