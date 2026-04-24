"""One-time migration: move bulk content out of state.json into savepoints.

Fields migrated (each moved to the noted savepoint step, then removed from
state.json):

- ``outline`` -> ``outline`` savepoint
- ``arc_assessment`` -> ``arc_assessment`` savepoint
- ``prompt_metadata.prompt_text`` -> ``raw_prompt`` savepoint
- ``chapters.{N}.expanded_outline`` -> ``expanded_chapter_{N}_{N}`` savepoint

If a savepoint already exists at the target step, the state-side value is
discarded rather than overwriting. A backup of the original state.json is
written next to it (``state.json.premigrate``) before any mutation.

Usage::

    python3 src/tools/migrate_state_slim.py --name <story>        # migrate one
    python3 src/tools/migrate_state_slim.py --all                 # migrate every story
    python3 src/tools/migrate_state_slim.py --name <story> --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_src_path = str(PROJECT_ROOT / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from infrastructure.storage.savepoint_repository import (  # noqa: E402
    FilesystemSavepointRepository,
)
from src.tools._io import STORIES_DIR, _validate_story_name  # noqa: E402


SIMPLE_FIELDS = [
    ("outline", "outline"),
    ("arc_assessment", "arc_assessment"),
]


def _repo_for(story_dir: Path) -> FilesystemSavepointRepository:
    repo = FilesystemSavepointRepository(base_path=story_dir)
    repo.set_story_directory("savepoints")
    return repo


def _coerce_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, default=str)


def _pop_nested(data: dict, path: list[str]) -> object | None:
    """Remove a nested key (dot path components) and return its previous value."""
    current = data
    for key in path[:-1]:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    if not isinstance(current, dict):
        return None
    return current.pop(path[-1], None)


def migrate_story(story_dir: Path, *, dry_run: bool = False) -> dict:
    """Migrate a single story. Returns a summary dict."""
    state_path = story_dir / "state.json"
    if not state_path.exists():
        return {"story": story_dir.name, "skipped": "no state.json"}

    with state_path.open() as f:
        state = json.load(f)

    repo = _repo_for(story_dir)
    moved: list[tuple[str, str, int]] = []  # (source_field, step, chars)
    skipped: list[tuple[str, str]] = []  # (source_field, reason)
    popped_any = False

    def _save_if_absent(step: str, value: str, source: str) -> None:
        if not value.strip():
            skipped.append((source, "empty value"))
            return
        already = asyncio.run(repo.has_savepoint(step))
        if already:
            skipped.append((source, f"savepoint '{step}' already exists"))
            return
        if not dry_run:
            asyncio.run(repo.save_savepoint(step, value))
        moved.append((source, step, len(value)))

    # Simple top-level fields
    for field, step in SIMPLE_FIELDS:
        if field in state:
            value = _coerce_text(state[field])
            _save_if_absent(step, value, field)
            if not dry_run:
                state.pop(field, None)
                popped_any = True

    # prompt_metadata.prompt_text -> raw_prompt
    if isinstance(state.get("prompt_metadata"), dict):
        pm = state["prompt_metadata"]
        if "prompt_text" in pm:
            value = _coerce_text(pm["prompt_text"])
            _save_if_absent("raw_prompt", value, "prompt_metadata.prompt_text")
            if not dry_run:
                pm.pop("prompt_text", None)
                popped_any = True

    # chapters.{N}.expanded_outline -> expanded_chapter_{N}_{N}
    chapters = state.get("chapters")
    if isinstance(chapters, dict):
        for key, chap in list(chapters.items()):
            if not isinstance(chap, dict):
                continue
            if "expanded_outline" not in chap:
                continue
            value = _coerce_text(chap["expanded_outline"])
            step = f"expanded_chapter_{key}_{key}"
            _save_if_absent(step, value, f"chapters.{key}.expanded_outline")
            if not dry_run:
                chap.pop("expanded_outline", None)
                popped_any = True

    if not dry_run and popped_any:
        backup = state_path.with_suffix(".json.premigrate")
        if not backup.exists():
            backup.write_text(state_path.read_text(encoding="utf-8"), encoding="utf-8")
        tmp = state_path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        tmp.replace(state_path)

    return {
        "story": story_dir.name,
        "dry_run": dry_run,
        "moved": [{"source": s, "step": step, "chars": n} for (s, step, n) in moved],
        "skipped": [{"source": s, "reason": r} for (s, r) in skipped],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", help="Story name to migrate")
    parser.add_argument(
        "--all", action="store_true", help="Migrate every story under stories/"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without writing",
    )
    args = parser.parse_args()

    if args.all:
        if not STORIES_DIR.exists():
            print(json.dumps({"migrated": []}))
            return
        summaries = []
        for story_dir in sorted(STORIES_DIR.iterdir()):
            if not story_dir.is_dir():
                continue
            if not (story_dir / "state.json").exists():
                continue
            summaries.append(migrate_story(story_dir, dry_run=args.dry_run))
        print(json.dumps(summaries, indent=2))
        return

    if not args.name:
        parser.error("Provide --name <story> or --all")
    story_dir = _validate_story_name(args.name)
    summary = migrate_story(story_dir, dry_run=args.dry_run)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
