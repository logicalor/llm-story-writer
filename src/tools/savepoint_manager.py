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

    # Auto-write milestone savepoints tied to terminal content savepoints.
    # Tool-owned savepoint writes drive milestone progress so the orchestrator
    # LLM cannot skip a `savepoint-mgr save <milestone>` step.
    milestone = _STEP_TO_MILESTONE.get(step)
    if milestone:
        try:
            asyncio.run(
                repo.save_savepoint(
                    milestone,
                    {"status": "complete", "source_step": step},
                )
            )
        except Exception as exc:
            print(
                f"Warning: milestone savepoint '{milestone}' auto-write failed: {exc}",
                file=sys.stderr,
            )

    print(json.dumps({"status": "saved", "step": step}, indent=2, default=str))


# Map a terminal content savepoint to the canonical milestone savepoint that
# records its completion. Writing any key on the left auto-writes the value on
# the right, so the LLM never needs a separate savepoint-mgr call for it.
_STEP_TO_MILESTONE: dict[str, str] = {
    "outline": "outline_complete",
    "refined_outline": "outline_complete",
    "arc_assessment": "arc_analysis_complete",
}


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


# Canonical phase order — must match the Savepoint Strategy table in
# prompts/agents/story-orchestrator.md. If the pipeline phases change,
# update both files together.
CANONICAL_PHASES: list[str] = [
    "init",
    "outline_complete",
    "arc_analysis_complete",
    "characters_complete",
    "settings_complete",
    "wiki_populated",
    "outlines_expanded",
    # chapter_{N}_complete handled separately (loop)
    "story_complete",
    "final_edit_complete",
]

PHASE_NEXT_DESCRIPTOR: dict[str, str] = {
    "": "Phase 1 (init)",
    "init": "Phase 2 (outline)",
    "outline_complete": "Phase 2.5 (arc analysis)",
    "arc_analysis_complete": "Phase 3 (approval) then Phase 4 (wiki init) then Phase 5 (characters & settings)",
    "characters_complete": "Phase 5 (settings)",
    "settings_complete": "Phase 6 (wiki population)",
    "wiki_populated": "Phase 7a (chapter outline expansion)",
    "outlines_expanded": "Phase 7b (per-chapter generation loop, starting at chapter 1)",
    "story_complete": "Phase 9 (final edit, if enabled)",
    "final_edit_complete": "complete — no further phases",
}


def cmd_next_phase(name: str) -> None:
    """Determine the next pipeline phase to run based on existing savepoints.

    Walks the canonical phase order and returns the highest-completed savepoint
    (gaps tolerated — a missing intermediate savepoint does not block detection
    of later ones). Detects per-chapter savepoints (`chapter_{N}_complete`)
    and reports the highest chapter number completed.
    """
    story_dir = _validate_story_name(name)
    if not story_dir.exists():
        print(f"Error: story not found: {name}", file=sys.stderr)
        sys.exit(1)

    repo = _make_repo(name)
    names = asyncio.run(repo.list_savepoint_names())
    name_set = set(names)

    # Find highest completed canonical phase (gaps tolerated)
    last_canonical = ""
    last_canonical_index = -1
    for idx, phase in enumerate(CANONICAL_PHASES):
        if phase in name_set:
            last_canonical = phase
            last_canonical_index = idx

    # Detect per-chapter savepoints (chapter_{N}_complete)
    chapter_numbers: list[int] = []
    for sp_name in names:
        if sp_name.startswith("chapter_") and sp_name.endswith("_complete"):
            middle = sp_name[len("chapter_") : -len("_complete")]
            if middle.isdigit():
                chapter_numbers.append(int(middle))
    last_chapter = max(chapter_numbers) if chapter_numbers else 0

    # Determine resume target
    # Per-chapter savepoints sit between wiki_populated and story_complete.
    # If any chapter savepoint exists, it is more recent than wiki_populated
    # but less recent than story_complete.
    if "story_complete" in name_set or "final_edit_complete" in name_set:
        last_completed = last_canonical
        next_phase = PHASE_NEXT_DESCRIPTOR.get(last_canonical, "unknown")
    elif last_chapter > 0:
        last_completed = f"chapter_{last_chapter}_complete"
        next_phase = (
            f"Phase 7 — chapter {last_chapter + 1}"
            if last_chapter > 0
            else "Phase 7 — chapter 1"
        )
    else:
        last_completed = last_canonical
        next_phase = PHASE_NEXT_DESCRIPTOR.get(last_canonical, "unknown")

    # Identify gaps in the canonical sequence below the highest completed phase
    missing_below_top: list[str] = []
    if last_canonical_index >= 0:
        for phase in CANONICAL_PHASES[:last_canonical_index]:
            if phase not in name_set:
                missing_below_top.append(phase)

    result = {
        "last_completed": last_completed,
        "next_phase": next_phase,
        "last_canonical": last_canonical,
        "last_chapter_complete": last_chapter,
        "missing_below_top": missing_below_top,
        "all_savepoints": names,
    }
    print(json.dumps(result, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage story savepoints.")
    parser.add_argument(
        "--operation",
        required=True,
        choices=[
            "save",
            "load",
            "has",
            "list",
            "list-full",
            "clear",
            "next-phase",
        ],
        help=(
            "Operation to perform. "
            "'list' returns names only (fast); "
            "'list-full' returns names + data (can be large); "
            "'next-phase' returns the deterministic resume target."
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

    elif args.operation == "next-phase":
        cmd_next_phase(args.name)


if __name__ == "__main__":
    main()
