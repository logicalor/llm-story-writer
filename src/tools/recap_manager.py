"""CLI tool for managing chapter recaps (load, generate, sanitize, compact)."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, NoReturn

if TYPE_CHECKING:
    from infrastructure.storage.savepoint_repository import (
        FilesystemSavepointRepository,
    )

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STORIES_DIR = Path(os.environ.get("STORIES_DIR", str(PROJECT_ROOT / "stories")))

_src_path = str(PROJECT_ROOT / "src")
_root_path = str(PROJECT_ROOT)
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)
if _root_path not in sys.path:
    sys.path.insert(0, _root_path)


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


def _validate_chapter(chapter: int) -> None:
    """Validate chapter number is positive."""
    if chapter < 1:
        print("Error: chapter must be >= 1", file=sys.stderr)
        sys.exit(2)


def _make_repo(name: str) -> FilesystemSavepointRepository:
    """Create a FilesystemSavepointRepository for the given story."""
    from infrastructure.storage.savepoint_repository import (
        FilesystemSavepointRepository,
    )

    repo = FilesystemSavepointRepository(base_path=STORIES_DIR / name)
    repo.set_story_directory("savepoints")
    return repo


def _load_savepoint(repo: FilesystemSavepointRepository, step: str) -> Any:
    """Load a savepoint, returning its data."""
    return asyncio.run(repo.load_savepoint(step))


def _save_savepoint(repo: FilesystemSavepointRepository, step: str, data: Any) -> None:
    """Save data to a savepoint."""
    asyncio.run(repo.save_savepoint(step, data))


def _has_savepoint(repo: FilesystemSavepointRepository, step: str) -> bool:
    """Check if a savepoint exists."""
    return asyncio.run(repo.has_savepoint(step))


def _load_prompt(prompt_id: str, variables: dict[str, Any] | None = None) -> str:
    """Load and render a prompt template."""
    from infrastructure.prompts.prompt_loader import PromptLoader

    loader = PromptLoader(prompts_dir=str(PROJECT_ROOT / "prompts"))
    return loader.load_prompt(prompt_id, variables)


def _call_llm(prompt: str, *, model: str | None = None) -> str:
    """Call LLM with a prompt and return text response."""
    from src.tools._llm import generate_text

    return generate_text(prompt, model=model)


def _extract_json_from_response(text: str) -> str:
    """Extract JSON from LLM response, stripping markdown fences."""
    from src.tools._llm import _extract_json_block

    return _extract_json_block(text)


def _success(operation: str, data: Any) -> None:
    """Print success response and exit."""
    print(
        json.dumps(
            {"status": "success", "operation": operation, "data": data},
            indent=2,
            default=str,
        )
    )


def _error(message: str, exit_code: int = 1) -> NoReturn:
    """Print error to stderr and exit."""
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(exit_code)


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------


def cmd_load(name: str, chapter: int, **_kwargs: Any) -> None:
    """Load recap from savepoint."""
    story_dir = _validate_story_name(name)
    _validate_chapter(chapter)
    if not story_dir.exists():
        _error(f"story not found: {name}")

    repo = _make_repo(name)
    step = f"chapter_{chapter}/recap"

    if not _has_savepoint(repo, step):
        _error(f"recap not found for chapter {chapter}")

    data = _load_savepoint(repo, step)
    _success("load", data)


def cmd_generate(
    name: str,
    chapter: int,
    story_start_date: str,
    *,
    model: str | None = None,
    **_kwargs: Any,
) -> None:
    """Generate recap for a chapter using 5-stage pipeline."""
    story_dir = _validate_story_name(name)
    _validate_chapter(chapter)
    if not story_dir.exists():
        _error(f"story not found: {name}")

    repo = _make_repo(name)

    # --- Load inputs ---
    content_step = f"chapter_{chapter}/content"
    if not _has_savepoint(repo, content_step):
        _error(f"chapter content not found at savepoint: {content_step}")
    chapter_content = _load_savepoint(repo, content_step)
    if not isinstance(chapter_content, str):
        chapter_content = json.dumps(chapter_content, default=str)

    # Optional: previous recap
    previous_recap = ""
    if chapter > 1:
        prev_step = f"chapter_{chapter - 1}/recap"
        if _has_savepoint(repo, prev_step):
            prev_data = _load_savepoint(repo, prev_step)
            previous_recap = (
                prev_data
                if isinstance(prev_data, str)
                else json.dumps(prev_data, default=str)
            )

    # --- Stage 1: Extract events ---
    try:
        prompt_1 = _load_prompt(
            "recap/extract_events",
            {"chapter_content": chapter_content, "chapter_num": str(chapter)},
        )
        events_raw = _call_llm(prompt_1, model=model)
        events = _extract_json_from_response(events_raw)
        _save_savepoint(repo, f"chapter_{chapter}/events", events)
    except Exception as exc:
        _error(f"stage 1 (extract events) failed: {exc}")

    # --- Stage 2: Assign timing ---
    try:
        prompt_2 = _load_prompt(
            "recap/assign_event_timing",
            {
                "events": events,
                "story_start_date": story_start_date,
                "previous_chapter_recap": previous_recap,
            },
        )
        timed_raw = _call_llm(prompt_2, model=model)
        timed_events = _extract_json_from_response(timed_raw)
        _save_savepoint(repo, f"chapter_{chapter}/timed_events", timed_events)
    except Exception as exc:
        _error(f"stage 2 (assign timing) failed: {exc}")

    # --- Stage 3: Enrich details ---
    try:
        prompt_3 = _load_prompt(
            "recap/enrich_event_details",
            {"timed_events": timed_events, "chapter_num": str(chapter)},
        )
        enriched_raw = _call_llm(prompt_3, model=model)
        enriched_events = _extract_json_from_response(enriched_raw)
        _save_savepoint(repo, f"chapter_{chapter}/enriched_events", enriched_events)
    except Exception as exc:
        _error(f"stage 3 (enrich details) failed: {exc}")

    # --- Stage 4: Format output ---
    try:
        prompt_4 = _load_prompt(
            "recap/format_json",
            {"enriched_events": enriched_events, "chapter_num": str(chapter)},
        )
        formatted_raw = _call_llm(prompt_4, model=model)
        formatted_recap = _extract_json_from_response(formatted_raw)
        _save_savepoint(repo, f"chapter_{chapter}/formatted_recap", formatted_recap)
    except Exception as exc:
        _error(f"stage 4 (format output) failed: {exc}")

    # --- Stage 5: Filter aged events (programmatic) ---
    try:
        recap_data = json.loads(formatted_recap)
    except json.JSONDecodeError:
        # If format step didn't return valid JSON, save as-is
        _save_savepoint(repo, f"chapter_{chapter}/recap", formatted_recap)
        _success("generate", formatted_recap)
        return

    filtered = _filter_low_importance_events(recap_data, story_start_date)
    final_recap = json.dumps(filtered, indent=2)

    _save_savepoint(repo, f"chapter_{chapter}/recap", final_recap)
    _success("generate", filtered)


def _filter_low_importance_events(
    recap_data: dict | list, story_start_date: str
) -> Any:
    """Filter events: keep only high-importance events (matching RecapManager logic)."""
    if not isinstance(recap_data, dict):
        return recap_data

    current_date = _extract_current_date(recap_data, story_start_date)

    if "events_by_timeline" in recap_data:
        timeline = recap_data["events_by_timeline"]
        for _key, section in timeline.items():
            if isinstance(section, dict) and "events" in section:
                events = section.get("events", [])
                if isinstance(events, list):
                    section["events"] = [
                        e for e in events if _should_keep_event(e, current_date)
                    ]
    elif "events" in recap_data and isinstance(recap_data["events"], list):
        recap_data["events"] = [
            e for e in recap_data["events"] if _should_keep_event(e, current_date)
        ]

    # Update meta total
    if "meta" in recap_data and isinstance(recap_data["meta"], dict):
        total = 0
        if "events_by_timeline" in recap_data:
            for section in recap_data["events_by_timeline"].values():
                if isinstance(section, dict) and "events" in section:
                    evts = section.get("events", [])
                    if isinstance(evts, list):
                        total += len(evts)
        elif "events" in recap_data and isinstance(recap_data["events"], list):
            total = len(recap_data["events"])
        recap_data["meta"]["total_events"] = total

    return recap_data


def _should_keep_event(event: Any, _current_date: str) -> bool:
    """Keep only high importance events — matches RecapManager._should_keep_event."""
    if not isinstance(event, dict):
        return True
    importance = event.get("importance", "medium")
    if not isinstance(importance, str):
        return True
    return importance.lower() == "high"


def _extract_current_date(recap_data: dict, story_start_date: str) -> str:
    """Extract current/latest date from recap data."""
    latest: str | None = None

    if "events_by_timeline" in recap_data:
        timeline = recap_data["events_by_timeline"]
        for section in timeline.values():
            if isinstance(section, dict) and "events" in section:
                for event in section.get("events", []):
                    if isinstance(event, dict) and "date_start" in event:
                        ds = event["date_start"]
                        if isinstance(ds, str) and (not latest or ds > latest):
                            latest = ds
    elif "events" in recap_data and isinstance(recap_data["events"], list):
        for event in recap_data["events"]:
            if isinstance(event, dict) and "date_start" in event:
                ds = event["date_start"]
                if isinstance(ds, str) and (not latest or ds > latest):
                    latest = ds

    if "meta" in recap_data and isinstance(recap_data["meta"], dict):
        led = recap_data["meta"].get("latest_event_date")
        if isinstance(led, str) and (not latest or led > latest):
            latest = led

    if latest:
        return latest.split(" ")[0] if " " in latest else latest
    return story_start_date


def cmd_sanitize(
    name: str,
    chapter: int,
    story_start_date: str,
    *,
    enable_programmatic_classification: bool = False,
    model: str | None = None,
    **_kwargs: Any,
) -> None:
    """Sanitize an existing recap."""
    story_dir = _validate_story_name(name)
    _validate_chapter(chapter)
    if not story_dir.exists():
        _error(f"story not found: {name}")

    repo = _make_repo(name)
    recap_step = f"chapter_{chapter}/recap"

    if not _has_savepoint(repo, recap_step):
        _error(f"recap not found for chapter {chapter}")

    recap_data = _load_savepoint(repo, recap_step)
    recap_str = (
        recap_data
        if isinstance(recap_data, str)
        else json.dumps(recap_data, default=str)
    )

    # Load previous recap if available
    previous_recap = ""
    if chapter > 1:
        prev_step = f"chapter_{chapter - 1}/recap"
        if _has_savepoint(repo, prev_step):
            prev_data = _load_savepoint(repo, prev_step)
            previous_recap = (
                prev_data
                if isinstance(prev_data, str)
                else json.dumps(prev_data, default=str)
            )

    # Call LLM with sanitize prompt
    try:
        prompt = _load_prompt(
            "recap/sanitize",
            {
                "recap": recap_str,
                "story_start_date": story_start_date,
                "previous_chapter_recap": previous_recap,
            },
        )
        sanitized_raw = _call_llm(prompt, model=model)
        sanitized = _extract_json_from_response(sanitized_raw)
    except Exception as exc:
        _error(f"sanitize LLM call failed: {exc}")

    # Optional: programmatic recency classification
    if enable_programmatic_classification:
        try:
            sanitized_data = json.loads(sanitized)
            current_date = _extract_current_date(sanitized_data, story_start_date)
            _classify_event_recency(sanitized_data, current_date)
            sanitized = json.dumps(sanitized_data, indent=2)
        except (json.JSONDecodeError, ValueError):
            pass  # keep LLM output as-is if not valid JSON

    # Save sanitized recap (overwrites)
    _save_savepoint(repo, recap_step, sanitized)

    # Parse for structured output if possible
    try:
        result = json.loads(sanitized)
    except json.JSONDecodeError:
        result = sanitized

    _success("sanitize", result)


def _classify_event_recency(data: dict, current_date: str) -> None:
    """Classify events by recency in-place (matches RecapManager logic)."""
    try:
        current_dt = datetime.strptime(current_date, "%Y-%m-%d")
    except ValueError:
        return

    events: list[dict[str, Any]] = []
    if "events" in data and isinstance(data["events"], list):
        events = data["events"]
    elif "events_by_timeline" in data:
        for section in data["events_by_timeline"].values():
            if isinstance(section, dict) and "events" in section:
                evts = section.get("events", [])
                if isinstance(evts, list):
                    events.extend(evts)

    for event in events:
        if not isinstance(event, dict):
            continue
        ds = event.get("date_start", "")
        if not isinstance(ds, str) or not ds:
            continue
        date_part = ds.split(" ")[0] if " " in ds else ds
        try:
            event_dt = datetime.strptime(date_part, "%Y-%m-%d")
        except ValueError:
            continue
        days_diff = (current_dt - event_dt).days
        if days_diff <= 0:
            event["recency"] = "current"
        elif days_diff <= 1:
            event["recency"] = "recent"
        elif days_diff <= 7:
            event["recency"] = "this_week"
        elif days_diff <= 30:
            event["recency"] = "this_month"
        else:
            event["recency"] = "historical"


def cmd_compact(
    name: str,
    chapter: int,
    *,
    model: str | None = None,
    **_kwargs: Any,
) -> None:
    """Compact recap events based on chapter number."""
    story_dir = _validate_story_name(name)
    _validate_chapter(chapter)
    if not story_dir.exists():
        _error(f"story not found: {name}")

    repo = _make_repo(name)
    recap_step = f"chapter_{chapter}/recap"

    if not _has_savepoint(repo, recap_step):
        _error(f"recap not found for chapter {chapter}")

    recap_data = _load_savepoint(repo, recap_step)
    recap_str = (
        recap_data
        if isinstance(recap_data, str)
        else json.dumps(recap_data, default=str)
    )

    # Determine compaction level
    if chapter <= 5:
        # No compaction for early chapters
        try:
            result = json.loads(recap_str) if isinstance(recap_str, str) else recap_str
        except json.JSONDecodeError:
            result = recap_str
        _success("compact", result)
        return

    if chapter <= 10:
        compaction_level = "light"
    elif chapter <= 20:
        compaction_level = "moderate"
    else:
        compaction_level = "heavy"

    # Call LLM with compact prompt
    try:
        prompt = _load_prompt(
            "recap/compact_events",
            {
                "recap": recap_str,
                "compaction_level": compaction_level,
                "chapter_num": str(chapter),
            },
        )
        compacted_raw = _call_llm(prompt, model=model)
        compacted = _extract_json_from_response(compacted_raw)
    except Exception as exc:
        _error(f"compact LLM call failed: {exc}")

    # Save compacted recap
    _save_savepoint(repo, f"chapter_{chapter}/compacted_recap", compacted)

    try:
        result = json.loads(compacted)
    except json.JSONDecodeError:
        result = compacted

    _success("compact", result)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage chapter recaps.")
    parser.add_argument(
        "--operation",
        required=True,
        choices=["load", "generate", "sanitize", "compact"],
        help="Operation to perform",
    )
    parser.add_argument("--name", required=True, help="Story name")
    parser.add_argument(
        "--chapter",
        type=int,
        default=None,
        help="Chapter number (required)",
    )
    parser.add_argument(
        "--story-start-date",
        default=None,
        help="Story start date (required for generate/sanitize)",
    )
    parser.add_argument(
        "--enable-programmatic-classification",
        action="store_true",
        default=False,
        help="Enable programmatic recency classification (sanitize only)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override LLM model identifier",
    )
    args = parser.parse_args()

    if args.chapter is None:
        print("Error: --chapter is required", file=sys.stderr)
        sys.exit(2)

    if args.operation == "load":
        cmd_load(args.name, args.chapter)

    elif args.operation == "generate":
        if not args.story_start_date:
            print(
                "Error: --story-start-date is required for generate",
                file=sys.stderr,
            )
            sys.exit(2)
        cmd_generate(
            args.name,
            args.chapter,
            args.story_start_date,
            model=args.model,
        )

    elif args.operation == "sanitize":
        if not args.story_start_date:
            print(
                "Error: --story-start-date is required for sanitize",
                file=sys.stderr,
            )
            sys.exit(2)
        cmd_sanitize(
            args.name,
            args.chapter,
            args.story_start_date,
            enable_programmatic_classification=args.enable_programmatic_classification,
            model=args.model,
        )

    elif args.operation == "compact":
        cmd_compact(args.name, args.chapter, model=args.model)


if __name__ == "__main__":
    main()
