"""CLI tool for managing story setting sheets."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STORIES_DIR = Path(os.environ.get("STORIES_DIR", str(PROJECT_ROOT / "stories")))


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


def _atomic_write(path: Path, content: str) -> None:
    """Write content atomically using tempfile + os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    fd_closed = False
    try:
        os.write(fd, content.encode())
        os.close(fd)
        fd_closed = True
        os.replace(tmp, str(path))
    except BaseException:
        if not fd_closed:
            os.close(fd)
        os.unlink(tmp)
        raise


def _slugify(setting_name: str) -> str:
    """Convert setting name to filesystem-safe slug."""
    slug = setting_name.lower().replace(" ", "-")
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


def _validate_setting_name(name: str, story_name: str) -> Path:
    """Validate setting name does not escape the settings directory."""
    if ".." in name:
        print(
            f"Error: setting name must not contain '..': {name}",
            file=sys.stderr,
        )
        sys.exit(1)
    slug = _slugify(name)
    if not slug:
        print(
            f"Error: setting name produces empty slug: {name}",
            file=sys.stderr,
        )
        sys.exit(1)
    settings_dir = (STORIES_DIR / story_name / "settings").resolve()
    setting_path = (settings_dir / f"{slug}.json").resolve()
    if not setting_path.is_relative_to(settings_dir):
        print(
            f"Error: setting name escapes settings directory: {name}",
            file=sys.stderr,
        )
        sys.exit(1)
    return setting_path


def cmd_extract_names(args: argparse.Namespace) -> None:
    """Extract setting names from LLM output."""
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
    """Generate and save a setting sheet."""
    if args.data is None:
        print("Error: --data is required for generate-sheet", file=sys.stderr)
        sys.exit(2)
    if not args.setting:
        print("Error: --setting is required for generate-sheet", file=sys.stderr)
        sys.exit(2)

    _validate_story_name(args.name)
    setting_path = _validate_setting_name(args.setting, args.name)

    try:
        data = json.loads(args.data)
    except json.JSONDecodeError:
        print("Error: --data is not valid JSON", file=sys.stderr)
        sys.exit(1)

    if not isinstance(data, dict):
        print("Error: --data must be a JSON object", file=sys.stderr)
        sys.exit(1)

    sheet_data = {
        "name": args.setting,
        "sheet": data.get("sheet", ""),
        "chunks": data.get("chunks", {}),
        "summary": data.get("summary", ""),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    _atomic_write(setting_path, json.dumps(sheet_data, indent=2))

    rel_path = str(setting_path.relative_to(STORIES_DIR.resolve().parent))
    print(json.dumps({"status": "ok", "path": rel_path}, indent=2))


def cmd_update_sheet(args: argparse.Namespace) -> None:
    """Update an existing setting sheet with partial data."""
    if args.data is None:
        print("Error: --data is required for update-sheet", file=sys.stderr)
        sys.exit(2)
    if not args.setting:
        print("Error: --setting is required for update-sheet", file=sys.stderr)
        sys.exit(2)

    _validate_story_name(args.name)
    setting_path = _validate_setting_name(args.setting, args.name)

    if not setting_path.exists():
        print(f"Error: setting sheet not found: {args.setting}", file=sys.stderr)
        sys.exit(1)

    try:
        existing = json.loads(setting_path.read_text())
    except json.JSONDecodeError:
        print(f"Error: corrupted setting sheet: {args.setting}", file=sys.stderr)
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

    _atomic_write(setting_path, json.dumps(existing, indent=2))

    rel_path = str(setting_path.relative_to(STORIES_DIR.resolve().parent))
    print(json.dumps({"status": "ok", "path": rel_path}, indent=2))


def cmd_load_sheet(args: argparse.Namespace) -> None:
    """Load a setting sheet from disk."""
    if not args.setting:
        print("Error: --setting is required for load-sheet", file=sys.stderr)
        sys.exit(2)

    _validate_story_name(args.name)
    setting_path = _validate_setting_name(args.setting, args.name)

    if not setting_path.exists():
        print(f"Error: setting sheet not found: {args.setting}", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(setting_path.read_text())
    except json.JSONDecodeError:
        print(f"Error: corrupted setting sheet: {args.setting}", file=sys.stderr)
        sys.exit(1)

    if args.abridged:
        data = {
            "name": data.get("name", ""),
            "summary": data.get("summary", ""),
            "updated_at": data.get("updated_at", ""),
        }

    print(json.dumps(data, indent=2))


def cmd_list(args: argparse.Namespace) -> None:
    """List all setting sheets for a story."""
    story_dir = _validate_story_name(args.name)
    settings_dir = story_dir / "settings"

    if not settings_dir.exists():
        print(json.dumps({"settings": []}, indent=2))
        return

    names: list[str] = []
    for path in sorted(settings_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text())
            names.append(data.get("name", path.stem))
        except (json.JSONDecodeError, OSError):
            names.append(path.stem)

    print(json.dumps({"settings": names}, indent=2))


def cmd_generate_abridged(args: argparse.Namespace) -> None:
    """Generate an abridged summary from a setting sheet."""
    if not args.setting:
        print("Error: --setting is required for generate-abridged", file=sys.stderr)
        sys.exit(2)

    _validate_story_name(args.name)
    setting_path = _validate_setting_name(args.setting, args.name)

    if not setting_path.exists():
        print(f"Error: setting sheet not found: {args.setting}", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(setting_path.read_text())
    except json.JSONDecodeError:
        print(f"Error: corrupted setting sheet: {args.setting}", file=sys.stderr)
        sys.exit(1)

    sheet_text = data.get("sheet", "")
    budget = args.budget
    word_limit = int(budget * 0.75)

    words = sheet_text.split()
    truncated = " ".join(words[:word_limit])

    data["summary"] = truncated
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    _atomic_write(setting_path, json.dumps(data, indent=2))

    rel_path = str(setting_path.relative_to(STORIES_DIR.resolve().parent))
    print(json.dumps({"summary": truncated, "path": rel_path}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage story setting sheets.")
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
        "--setting",
        default=None,
        help="Setting name (required for most operations)",
    )
    parser.add_argument(
        "--data",
        default=None,
        help="JSON string input (required for extract-names, generate-sheet, update-sheet)",
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
