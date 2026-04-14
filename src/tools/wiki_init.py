"""CLI tool for initialising a story wiki directory."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src = str(Path(__file__).resolve().parents[1])
if _src not in sys.path:
    sys.path.insert(0, _src)

from src.tools._io import _atomic_write  # noqa: E402
from src.tools._wiki import WIKI_SUBDIRS  # noqa: E402

STORIES_DIR = Path(os.environ.get("STORIES_DIR", str(PROJECT_ROOT / "stories")))
SCHEMA_TEMPLATE = Path(__file__).resolve().parent / "wiki_schema_template.md"


def _validate_story_name(name: str) -> Path:
    """Validate story name does not escape the stories directory."""
    story_dir = (STORIES_DIR / name).resolve()
    if not story_dir.is_relative_to(STORIES_DIR.resolve()):
        print(
            f"Error: story name escapes stories directory: {name}",
            file=sys.stderr,
        )
        sys.exit(1)
    return story_dir


def cmd_init(args: argparse.Namespace) -> None:
    """Initialise wiki directory structure for a story."""
    story_dir = _validate_story_name(args.name)

    if not story_dir.exists():
        print(f"Error: story directory not found: {args.name}", file=sys.stderr)
        sys.exit(1)

    wiki_dir = story_dir / "wiki"

    # Idempotent: if wiki already exists, report and exit
    if wiki_dir.exists():
        print(
            json.dumps(
                {
                    "status": "ok",
                    "wiki_dir": str(wiki_dir),
                    "created": False,
                    "already_exists": True,
                }
            )
        )
        return

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
        "# Wiki Index\n\n<!-- slug | type | name | aliases -->\n",
    )

    # Create empty log.md
    _atomic_write(wiki_dir / "log.md", "# Wiki Change Log\n")

    # Create empty contradictions.md
    _atomic_write(wiki_dir / "contradictions.md", "# Contradictions Log\n")

    print(
        json.dumps(
            {
                "status": "ok",
                "wiki_dir": str(wiki_dir),
                "created": True,
            }
        )
    )


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
