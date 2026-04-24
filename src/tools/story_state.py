"""CLI tool for managing story state (init, read, write, list)."""

import argparse
import fcntl
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.tools._io import STORIES_DIR, _validate_story_name  # noqa: E402


# --- Milestone savepoint auto-write ---
# Map a story-state field write to a canonical milestone savepoint so resume
# logic (savepoint-mgr next-phase) reflects actual pipeline progress without
# relying on the orchestrator LLM to remember a separate savepoint-mgr call.
#
# Keys are dot-notation field paths; values are the savepoint step name.
FIELD_TO_MILESTONE_SAVEPOINT: dict[str, str] = {
    "characters": "characters_complete",
    "settings": "settings_complete",
}

# Bulk content fields no longer stored in state.json. Writes to these fields
# must go through savepoint-mgr (or the tool that owns them). This prevents
# large content from bloating state.json and being pulled into agent context
# on every `story-state read`.
#
# Each entry maps the rejected field -> the canonical savepoint step that
# holds the same content. The error message directs callers to the savepoint.
FORBIDDEN_BULK_FIELDS: dict[str, str] = {
    "outline": "outline",
    "arc_assessment": "arc_assessment",
    "prompt_metadata.prompt_text": "raw_prompt",
}


def _is_forbidden_bulk_field(field: str) -> tuple[bool, str | None]:
    """Check whether a field is a bulk-content field that must live in savepoints.

    Returns (is_forbidden, suggested_savepoint_step).
    """
    if field in FORBIDDEN_BULK_FIELDS:
        return True, FORBIDDEN_BULK_FIELDS[field]
    # chapters.{N}.expanded_outline -> expanded_chapter_{N}_{N}
    parts = field.split(".")
    if (
        len(parts) == 3
        and parts[0] == "chapters"
        and parts[2] == "expanded_outline"
        and parts[1].isdigit()
    ):
        n = parts[1]
        return True, f"expanded_chapter_{n}_{n}"
    return False, None


def _write_milestone_savepoint(story_dir: Path, step: str, data: Any) -> None:
    """Write a milestone savepoint for the given story.

    Best-effort: logs to stderr on failure but does not raise, so a broken
    savepoint write never blocks a successful state mutation.
    """
    try:
        import asyncio as _asyncio  # noqa: PLC0415

        from infrastructure.storage.savepoint_repository import (  # noqa: PLC0415
            FilesystemSavepointRepository,
        )

        repo = FilesystemSavepointRepository(base_path=story_dir)
        repo.set_story_directory("savepoints")
        _asyncio.run(repo.save_savepoint(step, data))
    except Exception as exc:  # pragma: no cover — defensive
        print(
            f"Warning: milestone savepoint '{step}' write failed: {exc}",
            file=sys.stderr,
        )


def _value_is_non_empty(value: Any) -> bool:
    """True when a written field value represents real progress."""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


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
    "pipeline_state": {"phase": None, "step": None, "chapter": None},
}

DEFAULT_PIPELINE_STATE = {"phase": None, "step": None, "chapter": None}


def _ensure_state_defaults(data: dict) -> dict:
    """Backfill newly added state fields for older stories."""
    if "pipeline_state" not in data or not isinstance(data["pipeline_state"], dict):
        data["pipeline_state"] = DEFAULT_PIPELINE_STATE.copy()
    return data


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
        return _ensure_state_defaults(json.load(f))


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
    normalized_name = story_dir.name
    if story_dir.exists():
        print(f"Error: story already exists: {normalized_name}", file=sys.stderr)
        sys.exit(1)

    for subdir in ("chapters", "characters", "settings", "savepoints"):
        (story_dir / subdir).mkdir(parents=True, exist_ok=True)

    state_path = story_dir / "state.json"
    _write_state_atomic(state_path, INITIAL_STATE)
    _write_milestone_savepoint(
        story_dir, "init", {"status": "initialized", "story": normalized_name}
    )
    print(json.dumps({"status": "created", "story": normalized_name}))


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
    """Write a value to a nested field in story state. value_str is a JSON string."""
    story_dir = _validate_story_name(name)
    state_path = story_dir / "state.json"

    forbidden, suggested_step = _is_forbidden_bulk_field(field)
    if forbidden:
        print(
            f"Error: field '{field}' is a bulk-content field and must not be written to state.json. "
            f"Use: savepoint-mgr save --name {name} --step {suggested_step} --data <value>",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        if not value_str.startswith('"') or not value_str.endswith('"'):
            # Fallback for plain text that isn't explicitly quoted as a JSON string
            value = value_str
        else:
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
            data = _ensure_state_defaults(json.load(f))
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

    milestone_step = FIELD_TO_MILESTONE_SAVEPOINT.get(field)
    if milestone_step and _value_is_non_empty(value):
        _write_milestone_savepoint(
            story_dir,
            milestone_step,
            {"status": "complete", "source_field": field},
        )

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
    parser.add_argument(
        "--value",
        default=None,
        help="JSON string value for write. Use '-' to read JSON from stdin (safe for values containing quotes).",
    )
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
        value_str = sys.stdin.read() if args.value == "-" else args.value
        cmd_write(args.name, args.field, value_str)

    elif args.operation == "list":
        cmd_list()


if __name__ == "__main__":
    main()
