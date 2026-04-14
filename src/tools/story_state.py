"""CLI tool for managing story state (init, read, write, list)."""

import argparse
import fcntl
import json
import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.tools._io import STORIES_DIR, _validate_story_name  # noqa: E402

INITIAL_STATE = {
    "story_context": {
        "story_direction": "",
        "tone_style": "",
        "target_audience": "",
        "story_pacing": "medium",
        "current_themes": [],
        "world_rules": [],
        "genre_conventions": [],
        "current_tension": 1,
        "story_goals": [],
        "completed_arcs": [],
    },
    "characters": {},
    "plot_threads": {},
    "chapters": {},
}


def _get_nested(data: dict, field: str) -> object:
    """Get a nested value from a dict using dot-notation."""
    keys = field.split(".")
    current: object = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            print(f"Error: field not found: {field}", file=sys.stderr)
            sys.exit(1)
        current = current[key]
    return current


def _set_nested(data: dict, field: str, value: object) -> None:
    """Set a nested value in a dict using dot-notation, with deep merge for dicts."""
    keys = field.split(".")
    current = data
    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]

    last_key = keys[-1]
    # Deep merge if both existing and new values are dicts
    if (
        isinstance(value, dict)
        and last_key in current
        and isinstance(current[last_key], dict)
    ):
        _deep_merge(current[last_key], value)
    else:
        current[last_key] = value


def _deep_merge(target: dict, source: dict) -> None:
    """Recursively merge source into target without clobbering sibling fields."""
    for key, val in source.items():
        if key in target and isinstance(target[key], dict) and isinstance(val, dict):
            _deep_merge(target[key], val)
        else:
            target[key] = val


def _read_state(state_path: Path) -> dict:
    """Read state.json from disk."""
    if not state_path.exists():
        print(f"Error: state file not found: {state_path}", file=sys.stderr)
        sys.exit(1)
    with open(state_path) as f:
        return json.load(f)


def _write_state_atomic(state_path: Path, data: dict) -> None:
    """Write state.json atomically with file locking."""
    state_path.parent.mkdir(parents=True, exist_ok=True)
    fd = None
    try:
        fd = os.open(str(state_path), os.O_RDWR | os.O_CREAT)
        fcntl.flock(fd, fcntl.LOCK_EX)
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                dir=str(state_path.parent),
                suffix=".tmp",
                delete=False,
            ) as tmp:
                json.dump(data, tmp, indent=2)
                tmp.write("\n")
                tmp_path = tmp.name
            os.replace(tmp_path, str(state_path))
        except BaseException:
            if tmp_path is not None:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
            raise
    finally:
        if fd is not None:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)


def cmd_init(name: str) -> None:
    """Initialize a new story directory with empty state."""
    story_dir = _validate_story_name(name)
    if story_dir.exists():
        print(f"Error: story already exists: {name}", file=sys.stderr)
        sys.exit(1)

    for subdir in ("chapters", "characters", "settings", "savepoints"):
        (story_dir / subdir).mkdir(parents=True, exist_ok=True)

    state_path = story_dir / "state.json"
    _write_state_atomic(state_path, INITIAL_STATE)
    print(json.dumps({"status": "created", "story": name}))


def cmd_read(name: str, field: str | None) -> None:
    """Read story state, optionally extracting a nested field."""
    story_dir = _validate_story_name(name)
    state_path = story_dir / "state.json"
    data = _read_state(state_path)

    if field:
        result = _get_nested(data, field)
    else:
        result = data

    print(json.dumps(result, indent=2))


def cmd_write(name: str, field: str, value_str: str) -> None:
    """Write a value to a nested field in story state."""
    story_dir = _validate_story_name(name)
    state_path = story_dir / "state.json"

    try:
        value = json.loads(value_str)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON in --value: {e}", file=sys.stderr)
        sys.exit(1)

    if not state_path.exists():
        print(f"Error: state file not found: {state_path}", file=sys.stderr)
        sys.exit(1)

    fd = None
    try:
        fd = os.open(str(state_path), os.O_RDWR)
        fcntl.flock(fd, fcntl.LOCK_EX)

        # Read, modify, write all under the same lock to prevent TOCTOU
        with open(state_path) as f:
            data = json.load(f)
        _set_nested(data, field, value)

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                dir=str(state_path.parent),
                suffix=".tmp",
                delete=False,
            ) as tmp:
                json.dump(data, tmp, indent=2)
                tmp.write("\n")
                tmp_path = tmp.name
            os.replace(tmp_path, str(state_path))
        except BaseException:
            if tmp_path is not None:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
            raise
    finally:
        if fd is not None:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    print(json.dumps({"status": "updated", "field": field}))


def cmd_list() -> None:
    """List available story names."""
    if not STORIES_DIR.exists():
        print(json.dumps([]))
        return

    stories = sorted(
        d.name
        for d in STORIES_DIR.iterdir()
        if d.is_dir() and (d / "state.json").exists()
    )
    print(json.dumps(stories))


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage story state.")
    parser.add_argument(
        "--operation",
        required=True,
        choices=["init", "read", "write", "list"],
        help="Operation to perform",
    )
    parser.add_argument("--name", default=None, help="Story name")
    parser.add_argument("--field", default=None, help="Dot-notation field path")
    parser.add_argument("--value", default=None, help="JSON string value for write")
    args = parser.parse_args()

    if args.operation == "init":
        if not args.name:
            print("Error: --name is required for init", file=sys.stderr)
            sys.exit(2)
        cmd_init(args.name)

    elif args.operation == "read":
        if not args.name:
            print("Error: --name is required for read", file=sys.stderr)
            sys.exit(2)
        cmd_read(args.name, args.field)

    elif args.operation == "write":
        if not args.name:
            print("Error: --name is required for write", file=sys.stderr)
            sys.exit(2)
        if not args.field:
            print("Error: --field is required for write", file=sys.stderr)
            sys.exit(2)
        if args.value is None:
            print("Error: --value is required for write", file=sys.stderr)
            sys.exit(2)
        cmd_write(args.name, args.field, args.value)

    elif args.operation == "list":
        cmd_list()


if __name__ == "__main__":
    main()
