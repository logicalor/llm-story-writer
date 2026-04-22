"""CLI tool for managing story savepoints (save, load, has, list, clear)."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from infrastructure.storage.savepoint_repository import (
        FilesystemSavepointRepository,
    )

PROJECT_ROOT = Path(__file__).resolve().parents[2]

_src_path = str(PROJECT_ROOT / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.tools._io import _validate_story_name  # noqa: E402


def _validate_step(step: str, savepoints_dir: Path) -> None:
    """Validate step name does not contain path traversal."""
    if ".." in step:
        print(
            f"Error: step name must not contain '..': {step}",
            file=sys.stderr,
        )
        sys.exit(1)
    resolved = (savepoints_dir / step).resolve()
    if not resolved.is_relative_to(savepoints_dir.resolve()):
        print(
            f"Error: step name escapes savepoints directory: {step}",
            file=sys.stderr,
        )
        sys.exit(1)


def _make_repo(name: str) -> FilesystemSavepointRepository:
    """Create a FilesystemSavepointRepository for the given story."""
    from infrastructure.storage.savepoint_repository import (
        FilesystemSavepointRepository,
    )

    story_dir = _validate_story_name(name)
    repo = FilesystemSavepointRepository(base_path=story_dir)
    repo.set_story_directory("savepoints")
    return repo


def cmd_save(name: str, step: str, data_str: str) -> None:
    """Save data to a savepoint."""
    story_dir = _validate_story_name(name)
    if not story_dir.exists():
        print(f"Error: story not found: {name}", file=sys.stderr)
        sys.exit(1)
    _validate_step(step, story_dir / "savepoints")

    try:
        data = json.loads(data_str)
    except json.JSONDecodeError:
        data = data_str

    repo = _make_repo(name)
    asyncio.run(repo.save_savepoint(step, data))
    print(json.dumps({"status": "saved", "step": step}, indent=2, default=str))


def cmd_load(name: str, step: str) -> None:
    """Load data from a savepoint."""
    story_dir = _validate_story_name(name)
    if not story_dir.exists():
        print(f"Error: story not found: {name}", file=sys.stderr)
        sys.exit(1)
    _validate_step(step, story_dir / "savepoints")

    repo = _make_repo(name)
    data = asyncio.run(repo.load_savepoint(step))
    print(json.dumps({"step": step, "data": data}, indent=2, default=str))


def cmd_has(name: str, step: str) -> None:
    """Check if a savepoint exists."""
    story_dir = _validate_story_name(name)
    if not story_dir.exists():
        print(f"Error: story not found: {name}", file=sys.stderr)
        sys.exit(1)
    _validate_step(step, story_dir / "savepoints")

    repo = _make_repo(name)
    exists = asyncio.run(repo.has_savepoint(step))
    print(json.dumps({"step": step, "exists": exists}, indent=2, default=str))


def cmd_list(name: str) -> None:
    """List all savepoints for a story (names only, no data)."""
    story_dir = _validate_story_name(name)
    if not story_dir.exists():
        print(f"Error: story not found: {name}", file=sys.stderr)
        sys.exit(1)

    repo = _make_repo(name)
    names = asyncio.run(repo.list_savepoint_names())
    print(json.dumps({"savepoints": names}, indent=2))


def cmd_list_full(name: str) -> None:
    """List all savepoints with their full data (can be large)."""
    story_dir = _validate_story_name(name)
    if not story_dir.exists():
        print(f"Error: story not found: {name}", file=sys.stderr)
        sys.exit(1)

    repo = _make_repo(name)
    savepoints = asyncio.run(repo.list_savepoints())
    print(json.dumps({"savepoints": savepoints}, indent=2, default=str))


def cmd_clear(name: str) -> None:
    """Clear all savepoints for a story."""
    story_dir = _validate_story_name(name)
    if not story_dir.exists():
        print(f"Error: story not found: {name}", file=sys.stderr)
        sys.exit(1)

    repo = _make_repo(name)
    asyncio.run(repo.clear_all_savepoints())
    print(json.dumps({"status": "cleared"}, indent=2, default=str))


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage story savepoints.")
    parser.add_argument(
        "--operation",
        required=True,
        choices=["save", "load", "has", "list", "list-full", "clear"],
        help=(
            "Operation to perform. "
            "'list' returns names only (fast); "
            "'list-full' returns names + data (can be large)"
        ),
    )
    parser.add_argument("--name", required=True, help="Story name")
    parser.add_argument(
        "--step",
        default=None,
        help="Step name (required for save/load/has)",
    )
    parser.add_argument(
        "--data",
        default=None,
        help="Data to save (JSON string, required for save)",
    )
    args = parser.parse_args()

    if args.operation == "save":
        if not args.step:
            print("Error: --step is required for save", file=sys.stderr)
            sys.exit(2)
        if args.data is None:
            print("Error: --data is required for save", file=sys.stderr)
            sys.exit(2)
        cmd_save(args.name, args.step, args.data)

    elif args.operation == "load":
        if not args.step:
            print("Error: --step is required for load", file=sys.stderr)
            sys.exit(2)
        cmd_load(args.name, args.step)

    elif args.operation == "has":
        if not args.step:
            print("Error: --step is required for has", file=sys.stderr)
            sys.exit(2)
        cmd_has(args.name, args.step)

    elif args.operation == "list":
        cmd_list(args.name)

    elif args.operation == "list-full":
        cmd_list_full(args.name)

    elif args.operation == "clear":
        cmd_clear(args.name)


if __name__ == "__main__":
    main()
