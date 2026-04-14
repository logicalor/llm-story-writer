"""CLI tool for running critics against story outlines (run-critics, parse-scores, should-refine, generate-feedback)."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
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

CRITIC_TYPES = [
    "audiobook-producer",
    "book-club-moderator",
    "commercial-fiction-editor",
    "literary-fiction-reviewer",
    "publishing-acquisitions-editor",
    "subject-expert",
]


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


def _error(message: str, exit_code: int = 1) -> NoReturn:
    """Print error to stderr and exit."""
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(exit_code)


def _serialize_critique_result(result: Any) -> dict[str, Any]:
    """Serialize a CritiqueResult dataclass to a dict."""
    return {
        "critic_type": result.critic_type,
        "scores": [
            {
                "criterion": s.criterion,
                "score": s.score,
                "max_score": s.max_score,
                "percentage": s.percentage,
                "notes": s.notes,
            }
            for s in result.scores
        ],
        "summary": result.summary,
        "overall_score": result.overall_score,
    }


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------


def cmd_run_critics(
    name: str,
    iteration: int,
    content: str | None,
    *,
    model: str | None = None,
) -> None:
    """Run all 6 critic types against an outline."""
    from application.services.critique_parser import CritiqueParser

    story_dir = _validate_story_name(name)
    if not story_dir.exists():
        _error(f"story not found: {name}")

    repo = _make_repo(name)

    # Load outline content
    outline: str
    if content:
        outline = content
    else:
        # Try loading from savepoint
        if iteration > 1 and _has_savepoint(repo, f"outline_iteration_{iteration - 1}"):
            data = _load_savepoint(repo, f"outline_iteration_{iteration - 1}")
            outline = data if isinstance(data, str) else json.dumps(data, default=str)
        elif _has_savepoint(repo, "outline"):
            data = _load_savepoint(repo, "outline")
            outline = data if isinstance(data, str) else json.dumps(data, default=str)
        else:
            _error("no outline content provided and no outline savepoint found")

    parser = CritiqueParser()
    critique_results = []

    for critic_type in CRITIC_TYPES:
        try:
            prompt_content = _load_prompt(
                f"outline_review/{critic_type}", variables={"outline": outline}
            )
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an expert critic providing detailed, constructive "
                        "feedback on story outlines. Always follow the exact format "
                        "specified in the prompt."
                    ),
                },
                {"role": "user", "content": prompt_content},
            ]
            response = _call_llm_messages(messages, model=model)
            result = parser.parse_critique(critic_type, response)
            critique_results.append(result)
        except Exception as exc:
            print(
                f"Warning: critic {critic_type} failed: {exc}",
                file=sys.stderr,
            )

    # Compute averages
    average_scores = parser.get_average_scores(critique_results)
    overall_average = parser.get_overall_average_score(critique_results)

    # Save combined results
    savepoint_data = {
        "iteration": iteration,
        "critic_results": [_serialize_critique_result(r) for r in critique_results],
        "average_scores": average_scores,
        "overall_average": overall_average,
    }
    _save_savepoint(repo, f"critique_results_iteration_{iteration}", savepoint_data)

    _success("run-critics", savepoint_data)


def cmd_parse_scores(critic_type: str, response_text: str) -> None:
    """Parse scores from a single critic response."""
    from application.services.critique_parser import CritiqueParser

    if critic_type not in CRITIC_TYPES:
        _error(f"unknown critic type: {critic_type}. Valid: {', '.join(CRITIC_TYPES)}")

    parser = CritiqueParser()
    result = parser.parse_critique(critic_type, response_text)
    _success("parse-scores", _serialize_critique_result(result))


def cmd_should_refine(
    name: str,
    iteration: int,
    quality_threshold: float,
) -> None:
    """Determine if content meets quality threshold."""
    story_dir = _validate_story_name(name)
    if not story_dir.exists():
        _error(f"story not found: {name}")

    repo = _make_repo(name)
    step = f"critique_results_iteration_{iteration}"
    if not _has_savepoint(repo, step):
        _error(f"critique results not found for iteration {iteration}")

    data = _load_savepoint(repo, step)
    if not isinstance(data, dict):
        _error("invalid critique results format")

    average_scores: dict[str, float] = data.get("average_scores", {})
    overall_average: float = data.get("overall_average", 0.0)

    # 75% per-criterion floor is a domain invariant — any criterion scoring below
    # this indicates a fundamental quality issue regardless of overall average
    any_criterion_low = any(score < 75.0 for score in average_scores.values())
    # overall_average is raw score sum (max 100) — effectively a percentage
    overall_low = overall_average < quality_threshold

    should_refine = any_criterion_low or overall_low

    _success(
        "should-refine",
        {
            "should_refine": should_refine,
            "average_scores": average_scores,
            "overall_average": overall_average,
            "threshold": quality_threshold,
        },
    )


def cmd_generate_feedback(name: str, iteration: int) -> None:
    """Format critique results as structured markdown."""
    from application.services.critique_parser import (
        CritiqueParser,
        CritiqueResult,
        CritiqueScore,
    )

    story_dir = _validate_story_name(name)
    if not story_dir.exists():
        _error(f"story not found: {name}")

    repo = _make_repo(name)
    step = f"critique_results_iteration_{iteration}"
    if not _has_savepoint(repo, step):
        _error(f"critique results not found for iteration {iteration}")

    data = _load_savepoint(repo, step)
    if not isinstance(data, dict):
        _error("invalid critique results format")

    raw_results = data.get("critic_results", [])
    if not isinstance(raw_results, list):
        _error("invalid critic_results format: expected list")

    # Reconstruct CritiqueResult objects from serialized data
    critique_results: list[CritiqueResult] = []
    for raw in raw_results:
        if not isinstance(raw, dict):
            continue
        scores = [
            CritiqueScore(
                criterion=s["criterion"],
                score=s["score"],
                max_score=s["max_score"],
                percentage=s["percentage"],
                notes=s["notes"],
            )
            for s in raw.get("scores", [])
            if isinstance(s, dict)
        ]
        critique_results.append(
            CritiqueResult(
                critic_type=raw.get("critic_type", "unknown"),
                scores=scores,
                summary=raw.get("summary", ""),
                overall_score=raw.get("overall_score", 0.0),
            )
        )

    parser = CritiqueParser()
    feedback = parser.format_critique_feedback(critique_results)
    _success("generate-feedback", {"feedback": feedback})


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Run critics against story outlines")
    parser.add_argument(
        "--operation",
        required=True,
        choices=["run-critics", "parse-scores", "should-refine", "generate-feedback"],
        help="Operation to perform",
    )
    parser.add_argument("--name", help="Story name")
    parser.add_argument(
        "--iteration", type=int, default=1, help="Critique iteration number"
    )
    parser.add_argument(
        "--content", help="Content to critique (if not loading from savepoint)"
    )
    parser.add_argument("--critic-type", help="Critic type for parse-scores")
    parser.add_argument(
        "--response-text", help="Raw critic response text for parse-scores"
    )
    parser.add_argument(
        "--quality-threshold",
        type=float,
        default=85.0,
        help="Quality threshold for should-refine",
    )
    parser.add_argument("--model", help="Override LLM model identifier")

    args = parser.parse_args()
    op = args.operation

    if op == "run-critics":
        if not args.name:
            _error("--name required for run-critics", exit_code=2)
        cmd_run_critics(args.name, args.iteration, args.content, model=args.model)
    elif op == "parse-scores":
        if not args.critic_type:
            _error("--critic-type required for parse-scores", exit_code=2)
        if not args.response_text:
            _error("--response-text required for parse-scores", exit_code=2)
        cmd_parse_scores(args.critic_type, args.response_text)
    elif op == "should-refine":
        if not args.name:
            _error("--name required for should-refine", exit_code=2)
        cmd_should_refine(args.name, args.iteration, args.quality_threshold)
    elif op == "generate-feedback":
        if not args.name:
            _error("--name required for generate-feedback", exit_code=2)
        cmd_generate_feedback(args.name, args.iteration)


if __name__ == "__main__":
    main()
