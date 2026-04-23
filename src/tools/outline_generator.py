"""CLI tool for outline generation pipeline (analyze, elements, outline, expand, refine)."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, NoReturn

if TYPE_CHECKING:
    from infrastructure.storage.savepoint_repository import (
        FilesystemSavepointRepository,
    )

PROJECT_ROOT = Path(__file__).resolve().parents[2]

_src_path = str(PROJECT_ROOT / "src")
_root_path = str(PROJECT_ROOT)
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)
if _root_path not in sys.path:
    sys.path.insert(0, _root_path)

from src.tools._io import STORIES_DIR, _validate_story_name  # noqa: E402
from src.tools._llm import _extract_json_block  # noqa: E402

# Chunk types for story analysis
CHUNK_TYPES = (
    "core_story_foundation",
    "character_foundation",
    "setting_foundation",
    "plot_structure",
    "theme_message",
    "tone_style",
    "conflict_stakes",
    "world_rules_logic",
)


def _make_repo(name: str) -> FilesystemSavepointRepository:
    """Create a FilesystemSavepointRepository for the given story."""
    from infrastructure.storage.savepoint_repository import (
        FilesystemSavepointRepository,
    )

    story_dir = _validate_story_name(name, base_dir=STORIES_DIR)
    repo = FilesystemSavepointRepository(base_path=story_dir)
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
    """Call LLM with a single prompt and return text response."""
    from src.tools._llm import generate_text

    return generate_text(prompt, model=model)


def _call_llm_messages(
    messages: list[dict[str, str]], *, model: str | None = None
) -> str:
    """Call LLM with full conversation history and return text response."""
    from src.tools._llm import generate_text_messages

    return generate_text_messages(messages, model=model)


def _success(operation: str, data: Any) -> None:
    """Print success response and exit."""
    print(
        json.dumps(
            {"status": "success", "operation": operation, "data": data},
            indent=2,
            default=str,
        )
    )


def _error(message: str, data: Any | None = None, exit_code: int = 1) -> NoReturn:
    """Print error to stderr and exit."""
    if data is None:
        print(f"Error: {message}", file=sys.stderr)
    else:
        print(
            json.dumps(
                {"status": "error", "operation": message, "data": data},
                indent=2,
                default=str,
            ),
            file=sys.stderr,
        )
    sys.exit(exit_code)


_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


def _parse_story_start_date(raw: str) -> str:
    """Extract a YYYY-MM-DD date from an LLM response.

    Handles responses wrapped in <output> tags, code fences, or surrounded by
    commentary. Falls back to the stripped raw text if no date pattern matches.
    """
    if not isinstance(raw, str):
        raw = str(raw)
    # Strip common wrappers: <output> tags, code fences, quotes
    cleaned = re.sub(r"</?output[^>]*>", "", raw, flags=re.IGNORECASE)
    cleaned = re.sub(r"```[a-zA-Z]*\n?", "", cleaned)
    cleaned = cleaned.replace("```", "").strip().strip("\"'")
    match = _DATE_RE.search(cleaned)
    if match:
        return match.group(1)
    raise ValueError(f"no YYYY-MM-DD date found in response: {raw[:200]!r}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_PLACEHOLDER_RE = re.compile(r"\[[A-Z][^\]]{8,}\]")


def _is_stub_content(content: str) -> bool:
    """Return True if content looks like an unfilled template placeholder.

    Detects files that were written with schema/template text instead of real
    LLM output — e.g. ``**Core Premise:** [Summary of the main idea]``.  Three
    or more bracket-enclosed title-case phrases is a reliable signal; ordinary
    prose almost never contains that many.
    """
    return len(_PLACEHOLDER_RE.findall(content)) >= 3


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------


def cmd_analyze_prompt(
    name: str,
    prompt: str,
    *,
    model: str | None = None,
    **_kwargs: Any,
) -> None:
    """Analyze story prompt: understand prompt, generate 8 chunks, extract start date + base context."""
    story_dir = _validate_story_name(name)
    story_dir.mkdir(parents=True, exist_ok=True)

    repo = _make_repo(name)
    conversation: list[dict[str, str]] = []

    # --- Step 1: Understand prompt ---
    _cached_understand = None
    if _has_savepoint(repo, "understand_prompt"):
        _cached = _load_savepoint(repo, "understand_prompt")
        if not isinstance(_cached, str):
            _cached = json.dumps(_cached, default=str)
        if not _is_stub_content(_cached):
            _cached_understand = _cached

    if _cached_understand is not None:
        understand_response = _cached_understand
    else:
        try:
            understand_prompt_text = _load_prompt(
                "multistep/outline/understand_prompt", {"prompt": prompt}
            )
            conversation.append({"role": "user", "content": understand_prompt_text})
            understand_response = _call_llm_messages(conversation, model=model)
            if _is_stub_content(understand_response):
                _error(
                    "understand prompt returned schema-only placeholder content "
                    "(model echoed template instead of filling it in); "
                    "not saving. Re-run to retry."
                )
            _save_savepoint(repo, "understand_prompt", understand_response)
        except Exception as exc:
            _error(f"understand prompt failed: {exc}")

    # Rebuild conversation history with understand step
    if not conversation:
        understand_prompt_text = _load_prompt(
            "multistep/outline/understand_prompt", {"prompt": prompt}
        )
        conversation.append({"role": "user", "content": understand_prompt_text})
    conversation.append({"role": "assistant", "content": understand_response})

    # --- Step 2: Generate 8 analysis chunks ---
    for chunk_type in CHUNK_TYPES:
        step = f"story_analysis/{chunk_type}_chunk"
        if _has_savepoint(repo, step):
            chunk_content = _load_savepoint(repo, step)
            if not isinstance(chunk_content, str):
                chunk_content = json.dumps(chunk_content, default=str)
            # Append to conversation for continuity
            conversation.append(
                {
                    "role": "user",
                    "content": (
                        f"Please generate this analysis chunk:\n\n"
                        f"{_load_prompt(f'multistep/outline/create_{chunk_type}_chunk')}\n\n"
                        f"Story prompt: {prompt}"
                    ),
                }
            )
            conversation.append({"role": "assistant", "content": chunk_content})
            continue

        try:
            chunk_prompt = _load_prompt(f"multistep/outline/create_{chunk_type}_chunk")
            user_msg = (
                f"Please generate this analysis chunk:\n\n{chunk_prompt}\n\n"
                f"Story prompt: {prompt}"
            )
            conversation.append({"role": "user", "content": user_msg})
            chunk_response = _call_llm_messages(conversation, model=model)
            _save_savepoint(repo, step, chunk_response)
            conversation.append({"role": "assistant", "content": chunk_response})
        except Exception as exc:
            _error(f"chunk generation failed ({chunk_type}): {exc}")

    # --- Step 3: Extract story start date from core_story_foundation ---
    if _has_savepoint(repo, "story_start_date"):
        story_start_date = _load_savepoint(repo, "story_start_date")
        if not isinstance(story_start_date, str):
            story_start_date = json.dumps(story_start_date, default=str)
    else:
        try:
            core_chunk = _load_savepoint(
                repo, "story_analysis/core_story_foundation_chunk"
            )
            if not isinstance(core_chunk, str):
                core_chunk = json.dumps(core_chunk, default=str)
            date_prompt = _load_prompt(
                "multistep/outline/story_start_date", {"prompt": core_chunk}
            )
            raw_date = _call_llm(date_prompt, model=model)
            story_start_date = _parse_story_start_date(raw_date)
            _save_savepoint(repo, "story_start_date", story_start_date)
        except Exception:
            story_start_date = "Present day"
            _save_savepoint(repo, "story_start_date", story_start_date)

    # --- Step 4: Base context = core_story_foundation chunk ---
    if not _has_savepoint(repo, "base_context"):
        try:
            core_chunk = _load_savepoint(
                repo, "story_analysis/core_story_foundation_chunk"
            )
            if not isinstance(core_chunk, str):
                core_chunk = json.dumps(core_chunk, default=str)
            _save_savepoint(repo, "base_context", core_chunk)
            base_context = core_chunk
        except Exception:
            base_context = "Story development in progress"
            _save_savepoint(repo, "base_context", base_context)
    else:
        base_context = _load_savepoint(repo, "base_context")
        if not isinstance(base_context, str):
            base_context = json.dumps(base_context, default=str)

    _success(
        "analyze-prompt",
        {
            "chunks_generated": len(CHUNK_TYPES),
            "story_start_date": story_start_date,
            "base_context": base_context,
        },
    )


def cmd_generate_elements(name: str, **_kwargs: Any) -> None:
    """Combine all 8 analysis chunks into a single story_elements savepoint."""
    _validate_story_name(name)
    repo = _make_repo(name)

    combined_chunks: list[str] = []
    for chunk_type in CHUNK_TYPES:
        step = f"story_analysis/{chunk_type}_chunk"
        if not _has_savepoint(repo, step):
            _error(f"missing chunk savepoint: {step}")
        chunk_data = _load_savepoint(repo, step)
        chunk_text = (
            chunk_data
            if isinstance(chunk_data, str)
            else json.dumps(chunk_data, default=str)
        )
        header = chunk_type.replace("_", " ").title()
        combined_chunks.append(f"=== {header} ===\n{chunk_text}")

    story_elements = "\n\n".join(combined_chunks)
    _save_savepoint(repo, "story_elements", story_elements)

    _success("generate-elements", {"savepoint": "story_elements"})


def cmd_generate_outline(
    name: str,
    desired_chapters: int,
    *,
    prompt: str | None = None,
    model: str | None = None,
    **_kwargs: Any,
) -> None:
    """Generate initial outline from story elements + base context."""
    _validate_story_name(name)
    repo = _make_repo(name)

    if not _has_savepoint(repo, "story_elements"):
        _error("story_elements savepoint not found — run generate-elements first")
    story_elements = _load_savepoint(repo, "story_elements")
    if not isinstance(story_elements, str):
        story_elements = json.dumps(story_elements, default=str)

    if not _has_savepoint(repo, "base_context"):
        _error("base_context savepoint not found — run analyze-prompt first")
    base_context = _load_savepoint(repo, "base_context")
    if not isinstance(base_context, str):
        base_context = json.dumps(base_context, default=str)

    # Resolve prompt text
    if prompt:
        prompt_text = prompt
    elif _has_savepoint(repo, "understand_prompt"):
        prompt_text = _load_savepoint(repo, "understand_prompt")
        if not isinstance(prompt_text, str):
            prompt_text = json.dumps(prompt_text, default=str)
    else:
        _error("--prompt is required when understand_prompt savepoint missing")

    if _has_savepoint(repo, "initial_outline"):
        outline_text = _load_savepoint(repo, "initial_outline")
        if not isinstance(outline_text, str):
            outline_text = json.dumps(outline_text, default=str)
    else:
        try:
            outline_prompt = _load_prompt(
                "outline/create",
                {
                    "prompt": prompt_text,
                    "story_elements": story_elements,
                    "base_context": base_context,
                    "desired_chapters": str(desired_chapters),
                },
            )
            outline_text = _call_llm(outline_prompt, model=model)
            _save_savepoint(repo, "initial_outline", outline_text)
        except Exception as exc:
            _error(f"outline generation failed: {exc}")
    _success("generate-outline", {"outline": outline_text})


def cmd_expand_chapter(
    name: str,
    chunk_start: int,
    chunk_end: int,
    total_chapters: int,
    *,
    previous_chunks: str = "",
    continuity_summary: str = "",
    model: str | None = None,
    **_kwargs: Any,
) -> None:
    """Generate an outline chunk for a range of chapters, then analyze continuity."""
    _validate_story_name(name)
    repo = _make_repo(name)

    if not _has_savepoint(repo, "story_elements"):
        _error("story_elements savepoint not found — run generate-elements first")
    story_elements = _load_savepoint(repo, "story_elements")
    if not isinstance(story_elements, str):
        story_elements = json.dumps(story_elements, default=str)

    if not _has_savepoint(repo, "base_context"):
        _error("base_context savepoint not found — run analyze-prompt first")
    base_context = _load_savepoint(repo, "base_context")
    if not isinstance(base_context, str):
        base_context = json.dumps(base_context, default=str)

    # --- Generate chunk outline ---
    chunk_step = f"outline_chunk_{chunk_start}_{chunk_end}"
    if _has_savepoint(repo, chunk_step):
        chunk_text = _load_savepoint(repo, chunk_step)
        if not isinstance(chunk_text, str):
            chunk_text = json.dumps(chunk_text, default=str)
    else:
        try:
            chunk_prompt = _load_prompt(
                "outline/create_chunk",
                {
                    "story_elements": story_elements,
                    "base_context": base_context,
                    "chunk_start": str(chunk_start),
                    "chunk_end": str(chunk_end),
                    "total_chapters": str(total_chapters),
                    "previous_chunks": previous_chunks,
                    "continuity_summary": continuity_summary,
                },
            )
            chunk_text = _call_llm(chunk_prompt, model=model)
            _save_savepoint(repo, chunk_step, chunk_text)
        except Exception as exc:
            _error(f"chunk expansion failed: {exc}")

    # --- Analyze continuity ---
    continuity_step = f"continuity_{chunk_start}_{chunk_end}"
    if _has_savepoint(repo, continuity_step):
        continuity_analysis = _load_savepoint(repo, continuity_step)
        if not isinstance(continuity_analysis, str):
            continuity_analysis = json.dumps(continuity_analysis, default=str)
    else:
        continuity_analysis = ""
        try:
            # Determine last chapter in previous chunks
            last_prev = str(chunk_start - 1) if chunk_start > 1 else "0"

            # Load enrichment suggestions if available
            enrichment = ""
            if _has_savepoint(repo, "enrichment_suggestions"):
                enr_data = _load_savepoint(repo, "enrichment_suggestions")
                enrichment = (
                    enr_data
                    if isinstance(enr_data, str)
                    else json.dumps(enr_data, default=str)
                )

            # Build combined previous chunks text including this new chunk
            all_previous = previous_chunks
            if all_previous:
                all_previous += "\n\n"
            all_previous += chunk_text

            continuity_prompt = _load_prompt(
                "outline/analyze_continuity",
                {
                    "story_elements": story_elements,
                    "base_context": base_context,
                    "enrichment_suggestions": enrichment,
                    "previous_chunks": all_previous,
                    "chunk_start": str(chunk_end + 1),
                    "chunk_end": str(
                        min(chunk_end + (chunk_end - chunk_start + 1), total_chapters)
                    ),
                    "total_chapters": str(total_chapters),
                    "last_chapter_in_previous": last_prev,
                },
            )
            continuity_analysis = _call_llm(continuity_prompt, model=model)
            _save_savepoint(repo, continuity_step, continuity_analysis)
        except Exception as exc:
            print(
                f"Warning: continuity analysis failed: {exc}",
                file=sys.stderr,
            )

    _success(
        "expand-chapter",
        {
            "chunk_outline": chunk_text,
            "continuity_analysis": continuity_analysis,
        },
    )


def cmd_expand_to_scenes(
    name: str,
    chapter_num: int,
    chapter_synopsis: str,
    scenes_min: int,
    scenes_max: int,
    *,
    previous_recap: str = "",
    next_chapter_synopsis: str = "",
    model: str | None = None,
    **_kwargs: Any,
) -> None:
    """Expand a chapter synopsis into validated scene definitions."""
    _validate_story_name(name)

    if not (1 <= scenes_min <= scenes_max <= 30):
        _error(
            "expand-to-scenes validation failed: scenes_min must be >= 1, "
            "scenes_max must be <= 30, and scenes_min must be <= scenes_max"
        )

    if not chapter_synopsis or not chapter_synopsis.strip():
        _error("expand-to-scenes: --chapter-synopsis cannot be empty")

    repo = _make_repo(name)

    if not _has_savepoint(repo, "story_elements"):
        _error("story_elements savepoint not found — run generate-elements first")
    story_elements = _load_savepoint(repo, "story_elements")
    if not isinstance(story_elements, str):
        story_elements = json.dumps(story_elements, default=str)

    if not _has_savepoint(repo, "base_context"):
        _error("base_context savepoint not found — run analyze-prompt first")
    base_context = _load_savepoint(repo, "base_context")
    if not isinstance(base_context, str):
        base_context = json.dumps(base_context, default=str)

    prompt_text = _load_prompt(
        "chapters/expand_to_scenes",
        {
            "chapter_synopsis": chapter_synopsis,
            "scenes_min": str(scenes_min),
            "scenes_max": str(scenes_max),
            "previous_chapter_recap": previous_recap,
            "next_chapter_synopsis": next_chapter_synopsis,
            "story_elements": story_elements,
            "base_context": base_context,
        },
    )

    required_keys = {
        "title",
        "description",
        "characters",
        "setting",
        "conflict",
        "tone",
        "key_events",
        "dialogue",
        "ending",
        "lead_in_to_next_scene",
        "literary_devices",
    }

    def _validate_scene_list(response_text: str) -> list[dict[str, Any]]:
        raw = _extract_json_block(response_text)
        scenes = json.loads(raw)
        if not isinstance(scenes, list):
            raise ValueError("scene output must be a JSON array")
        if not (scenes_min <= len(scenes) <= scenes_max):
            raise ValueError(
                f"scene count {len(scenes)} outside allowed range [{scenes_min}, {scenes_max}]"
            )

        validated_scenes: list[dict[str, Any]] = []
        for index, scene in enumerate(scenes, start=1):
            if not isinstance(scene, dict):
                raise ValueError(f"scene {index} must be a JSON object")

            missing_keys = required_keys - scene.keys()
            if missing_keys:
                missing = ", ".join(sorted(missing_keys))
                raise ValueError(f"scene {index} missing required keys: {missing}")

            validated_scenes.append(scene)

        return validated_scenes

    last_error: Exception | None = None
    scenes: list[dict[str, Any]] | None = None
    for _attempt in range(2):
        try:
            response_text = _call_llm(prompt_text, model=model)
            scenes = _validate_scene_list(response_text)
            break
        except (json.JSONDecodeError, RuntimeError, ValueError) as exc:
            last_error = exc

    if scenes is None:
        detail = str(last_error) if last_error is not None else "unknown error"
        _error(
            "expand-to-scenes",
            {
                "error": "LLM failed to produce valid scene JSON after retry",
                "detail": detail,
            },
        )

    step = f"chapter_{chapter_num}/scene_definitions"
    _save_savepoint(repo, step, scenes)
    _success(
        "expand-to-scenes",
        {
            "scene_count": len(scenes),
            "savepoint_step": step,
        },
    )


def cmd_refine(
    name: str,
    feedback: str,
    *,
    model: str | None = None,
    **_kwargs: Any,
) -> None:
    """Refine the outline based on feedback/critique."""
    _validate_story_name(name)
    repo = _make_repo(name)

    if not _has_savepoint(repo, "initial_outline"):
        _error("initial_outline savepoint not found — run generate-outline first")
    current_outline = _load_savepoint(repo, "initial_outline")
    if not isinstance(current_outline, str):
        current_outline = json.dumps(current_outline, default=str)

    if not _has_savepoint(repo, "story_elements"):
        _error("story_elements savepoint not found — run generate-elements first")
    story_elements = _load_savepoint(repo, "story_elements")
    if not isinstance(story_elements, str):
        story_elements = json.dumps(story_elements, default=str)

    if not _has_savepoint(repo, "base_context"):
        _error("base_context savepoint not found — run analyze-prompt first")
    base_context = _load_savepoint(repo, "base_context")
    if not isinstance(base_context, str):
        base_context = json.dumps(base_context, default=str)

    # Load optional context from savepoints if available
    character_context = ""
    if _has_savepoint(repo, "character_sheets"):
        cs_data = _load_savepoint(repo, "character_sheets")
        character_context = (
            cs_data if isinstance(cs_data, str) else json.dumps(cs_data, default=str)
        )

    setting_context = ""
    if _has_savepoint(repo, "setting_sheets"):
        ss_data = _load_savepoint(repo, "setting_sheets")
        setting_context = (
            ss_data if isinstance(ss_data, str) else json.dumps(ss_data, default=str)
        )

    # TODO: load wanted_chapters from story config when available
    wanted_chapters = ""

    try:
        refinement_prompt = _load_prompt(
            "outline/analyze_enrichment",
            {
                "story_elements": story_elements,
                "base_context": base_context,
                "character_context": character_context,
                "setting_context": setting_context,
                "wanted_chapters": wanted_chapters,
                "current_scope": current_outline,
            },
        )
        # Incorporate user feedback into the prompt so the LLM sees the critique
        refinement_prompt += (
            "\n\n## USER FEEDBACK / CRITIQUE\n\n"
            "Apply the following feedback when refining the outline:\n\n"
            f"{feedback}"
        )
        refined_text = _call_llm(refinement_prompt, model=model)
        _save_savepoint(repo, "refined_outline", refined_text)
        _success("refine", {"refined_outline": refined_text})
    except Exception as exc:
        _error(f"refinement failed: {exc}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Outline generation pipeline.")
    parser.add_argument(
        "--operation",
        required=True,
        choices=[
            "analyze-prompt",
            "generate-elements",
            "generate-outline",
            "expand-chapter",
            "expand-to-scenes",
            "refine",
        ],
        help="Operation to perform",
    )
    parser.add_argument("--name", required=True, help="Story name")
    parser.add_argument("--prompt", default=None, help="Story prompt text")
    parser.add_argument(
        "--desired-chapters",
        type=int,
        default=None,
        help="Number of desired chapters (generate-outline)",
    )
    parser.add_argument(
        "--chunk-start",
        type=int,
        default=None,
        help="Start chapter for chunk expansion",
    )
    parser.add_argument(
        "--chunk-end",
        type=int,
        default=None,
        help="End chapter for chunk expansion",
    )
    parser.add_argument(
        "--total-chapters",
        type=int,
        default=None,
        help="Total chapters in story (expand-chapter)",
    )
    parser.add_argument(
        "--previous-chunks",
        default="",
        help="Previous chunk outlines text (expand-chapter)",
    )
    parser.add_argument(
        "--continuity-summary",
        default="",
        help="Continuity summary text (expand-chapter)",
    )
    parser.add_argument(
        "--feedback",
        default=None,
        help="Critique/feedback text (refine)",
    )
    parser.add_argument(
        "--chapter-num",
        type=int,
        default=None,
        help="Chapter number for expand-to-scenes",
    )
    parser.add_argument(
        "--chapter-synopsis",
        default="",
        help="Chapter synopsis to expand into scenes",
    )
    parser.add_argument(
        "--scenes-min",
        type=int,
        default=8,
        help="Minimum scenes per chapter",
    )
    parser.add_argument(
        "--scenes-max",
        type=int,
        default=16,
        help="Maximum scenes per chapter",
    )
    parser.add_argument(
        "--previous-recap",
        default="",
        help="Previous chapter recap for continuity",
    )
    parser.add_argument(
        "--next-chapter-synopsis",
        default="",
        help="Next chapter synopsis for lead-in",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override LLM model identifier",
    )
    args = parser.parse_args()

    if args.operation == "analyze-prompt":
        if not args.prompt:
            print(
                "Error: --prompt is required for analyze-prompt",
                file=sys.stderr,
            )
            sys.exit(2)
        cmd_analyze_prompt(args.name, args.prompt, model=args.model)

    elif args.operation == "generate-elements":
        cmd_generate_elements(args.name)

    elif args.operation == "generate-outline":
        if args.desired_chapters is None:
            print(
                "Error: --desired-chapters is required for generate-outline",
                file=sys.stderr,
            )
            sys.exit(2)
        if args.desired_chapters < 1:
            _error("--desired-chapters must be >= 1")
        cmd_generate_outline(
            args.name,
            args.desired_chapters,
            prompt=args.prompt,
            model=args.model,
        )

    elif args.operation == "expand-chapter":
        if (
            args.chunk_start is None
            or args.chunk_end is None
            or args.total_chapters is None
        ):
            print(
                "Error: --chunk-start, --chunk-end, --total-chapters required for expand-chapter",
                file=sys.stderr,
            )
            sys.exit(2)
        if args.chunk_start < 1:
            _error("--chunk-start must be >= 1")
        if args.chunk_end < args.chunk_start:
            _error("--chunk-end must be >= --chunk-start")
        if args.total_chapters < args.chunk_end:
            _error("--total-chapters must be >= --chunk-end")
        cmd_expand_chapter(
            args.name,
            args.chunk_start,
            args.chunk_end,
            args.total_chapters,
            previous_chunks=args.previous_chunks,
            continuity_summary=args.continuity_summary,
            model=args.model,
        )

    elif args.operation == "expand-to-scenes":
        if args.chapter_num is None:
            print(
                "Error: --chapter-num required for expand-to-scenes",
                file=sys.stderr,
            )
            sys.exit(2)
        cmd_expand_to_scenes(
            args.name,
            args.chapter_num,
            args.chapter_synopsis,
            args.scenes_min,
            args.scenes_max,
            previous_recap=args.previous_recap,
            next_chapter_synopsis=args.next_chapter_synopsis,
            model=args.model,
        )

    elif args.operation == "refine":
        if not args.feedback:
            print(
                "Error: --feedback is required for refine",
                file=sys.stderr,
            )
            sys.exit(2)
        cmd_refine(args.name, args.feedback, model=args.model)


if __name__ == "__main__":
    main()
