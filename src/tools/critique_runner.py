"""CLI tool for running critics against story content."""

from __future__ import annotations

import argparse
import asyncio
import json
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

from src.tools._io import _validate_story_name  # noqa: E402

# Keep in sync with src/presentation/agents/outline_critic.py::OUTLINE_CRITIC_TYPES
OUTLINE_CRITIC_TYPES = [
    "audiobook-producer",
    "book-club-moderator",
    "commercial-fiction-editor",
    "literary-fiction-reviewer",
    "publishing-acquisitions-editor",
    "subject-expert",
]

CHAPTER_CRITIC_TYPES = [
    "commercial-fiction-editor",
    "chapter-pacing",
    "chapter-character-consistency",
]

CHARACTER_VOICE_CRITIC_TYPES = [
    "character-voice-consistency",
]

MODES = ["outline", "chapter", "character-voice"]


def _make_repo(name: str) -> FilesystemSavepointRepository:
    """Create a FilesystemSavepointRepository for the given story."""
    from infrastructure.storage.savepoint_repository import (
        FilesystemSavepointRepository,
    )

    story_dir = _validate_story_name(name)
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


def _critique_results_step(mode: str, iteration: int) -> str:
    """Return the namespaced critique savepoint key for the selected mode."""
    return f"{mode}_critique_results_iteration_{iteration}"


def _prompt_prefix(mode: str) -> str:
    """Return the prompt subdirectory for the selected critique mode."""
    if mode == "chapter":
        return "chapter_review"
    if mode == "character-voice":
        return "chapter_review"
    return "outline_review"


def _critic_types_for_mode(mode: str) -> list[str]:
    """Return the critic set for the selected critique mode."""
    if mode == "chapter":
        return CHAPTER_CRITIC_TYPES
    if mode == "character-voice":
        return CHARACTER_VOICE_CRITIC_TYPES
    return OUTLINE_CRITIC_TYPES


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------


def cmd_run_critics(
    name: str,
    iteration: int,
    content: str | None,
    *,
    mode: str = "outline",
    model: str | None = None,
) -> None:
    """Run all critics for the selected mode against story content."""
    from src.tools.critique_parser import CritiqueParser

    story_dir = _validate_story_name(name)
    if not story_dir.exists():
        _error(f"story not found: {name}")

    repo = _make_repo(name)

    if content is None:
        savepoint_steps: list[str] = []
        if mode == "chapter":
            savepoint_steps.extend(
                [
                    "chapter_assembled",
                    f"chapter_{iteration}_complete",
                    f"chapter_{iteration}/complete",
                ]
            )
        else:
            if iteration > 1:
                savepoint_steps.append(f"outline_iteration_{iteration - 1}")
            savepoint_steps.append("outline")

        for step in savepoint_steps:
            if _has_savepoint(repo, step):
                data = _load_savepoint(repo, step)
                content = (
                    data if isinstance(data, str) else json.dumps(data, default=str)
                )
                break

        if content is None:
            _error(
                f"no content provided for {mode} critique and no {mode} savepoint found"
            )

    parser = CritiqueParser()
    critique_results = []

    for critic_type in _critic_types_for_mode(mode):
        try:
            prompt_content = _load_prompt(
                f"{_prompt_prefix(mode)}/{critic_type}", variables={"outline": content}
            )
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an expert critic providing detailed, constructive "
                        "feedback on story content. Always follow the exact format "
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
        "mode": mode,
        "critic_results": [_serialize_critique_result(r) for r in critique_results],
        "average_scores": average_scores,
        "overall_average": overall_average,
    }
    _save_savepoint(repo, _critique_results_step(mode, iteration), savepoint_data)

    _success("run-critics", savepoint_data)


def cmd_parse_scores(
    critic_type: str, response_text: str, *, mode: str = "outline"
) -> None:
    """Parse scores from a single critic response."""
    from src.tools.critique_parser import CritiqueParser

    valid_critics = _critic_types_for_mode(mode)
    if critic_type not in valid_critics:
        _error(f"unknown critic type: {critic_type}. Valid: {', '.join(valid_critics)}")

    parser = CritiqueParser()
    result = parser.parse_critique(critic_type, response_text)
    _success("parse-scores", _serialize_critique_result(result))


def cmd_should_refine(
    name: str,
    iteration: int,
    quality_threshold: float,
    criterion_floor: float,
    *,
    mode: str = "outline",
) -> None:
    """Determine if content meets quality threshold."""
    story_dir = _validate_story_name(name)
    if not story_dir.exists():
        _error(f"story not found: {name}")

    repo = _make_repo(name)
    step = _critique_results_step(mode, iteration)
    if not _has_savepoint(repo, step):
        _error(f"critique results not found for iteration {iteration}")

    data = _load_savepoint(repo, step)
    if not isinstance(data, dict):
        _error("invalid critique results format")

    average_scores: dict[str, float] = data.get("average_scores", {})
    overall_average: float = data.get("overall_average", 0.0)

    any_criterion_low = any(
        score < criterion_floor for score in average_scores.values()
    )
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
            "criterion_floor": criterion_floor,
        },
    )


def cmd_generate_feedback(name: str, iteration: int, *, mode: str = "outline") -> None:
    """Format critique results as structured markdown."""
    from src.tools.critique_parser import (
        CritiqueParser,
        CritiqueResult,
        CritiqueScore,
    )

    story_dir = _validate_story_name(name)
    if not story_dir.exists():
        _error(f"story not found: {name}")

    repo = _make_repo(name)
    step = _critique_results_step(mode, iteration)
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


def cmd_run_arc_analysis(
    name: str,
    content: str,
    critic_summary: str = "",
    *,
    model: str | None = None,
) -> None:
    """Run the three arc analysis prompts and return a structured assessment."""
    story_dir = _validate_story_name(name)
    if not story_dir.exists():
        _error(f"story not found: {name}")

    repo = _make_repo(name)

    # Step 1: Arc distribution analysis
    arc_dist_prompt = _load_prompt("outline_arc/arc_distribution", {"outline": content})
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert story structure analyst. "
                "Analyse the outline carefully and follow the exact format specified."
            ),
        },
        {"role": "user", "content": arc_dist_prompt},
    ]
    arc_distribution = _call_llm_messages(messages, model=model)
    _save_savepoint(repo, "arc_distribution", arc_distribution)

    # Step 2: Promise/payoff analysis
    promise_prompt = _load_prompt("outline_arc/promise_payoff", {"outline": content})
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert story structure analyst. "
                "Analyse the outline carefully and follow the exact format specified."
            ),
        },
        {"role": "user", "content": promise_prompt},
    ]
    promise_payoff = _call_llm_messages(messages, model=model)
    _save_savepoint(repo, "arc_promise_payoff", promise_payoff)

    # Step 3: Synthesis
    synthesis_prompt = _load_prompt(
        "outline_arc/arc_synthesis",
        {
            "outline": content,
            "critic_summary": critic_summary,
            "arc_distribution": arc_distribution,
            "promise_payoff": promise_payoff,
        },
    )
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert story structure analyst. "
                "Analyse the outline carefully and follow the exact format specified."
            ),
        },
        {"role": "user", "content": synthesis_prompt},
    ]
    arc_assessment = _call_llm_messages(messages, model=model)
    _save_savepoint(repo, "arc_assessment", arc_assessment)
    try:
        _save_savepoint(
            repo,
            "arc_analysis_complete",
            {"status": "complete", "source_step": "arc_assessment"},
        )
    except Exception as exc:
        print(
            f"Warning: arc_analysis_complete savepoint write failed: {exc}",
            file=sys.stderr,
        )

    verdict_code = "significant_issues"
    if "✅" in arc_assessment or "Strong arc" in arc_assessment:
        verdict_code = "strong"
    elif "⚠️" in arc_assessment or "Minor arc concerns" in arc_assessment:
        verdict_code = "minor_concerns"

    _success(
        "run-arc-analysis",
        {
            "arc_assessment": arc_assessment,
            "verdict_code": verdict_code,
            "arc_distribution": arc_distribution,
            "promise_payoff": promise_payoff,
        },
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Run critics against story content")
    parser.add_argument(
        "--operation",
        required=True,
        choices=[
            "run-critics",
            "parse-scores",
            "should-refine",
            "generate-feedback",
            "run-arc-analysis",
        ],
        help="Operation to perform",
    )
    parser.add_argument(
        "--mode",
        choices=MODES,
        default="outline",
        help="Critique mode: outline or chapter",
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
    parser.add_argument(
        "--criterion-floor",
        type=float,
        default=75.0,
        help="Minimum allowed per-criterion score for should-refine",
    )
    parser.add_argument("--model", help="Override LLM model identifier")
    parser.add_argument(
        "--critic-summary",
        default="",
        help="Optional critic summary for arc synthesis",
    )

    args = parser.parse_args()
    op = args.operation

    if op == "run-critics":
        if not args.name:
            _error("--name required for run-critics", exit_code=2)
        cmd_run_critics(
            args.name,
            args.iteration,
            args.content,
            mode=args.mode,
            model=args.model,
        )
    elif op == "parse-scores":
        if not args.critic_type:
            _error("--critic-type required for parse-scores", exit_code=2)
        if not args.response_text:
            _error("--response-text required for parse-scores", exit_code=2)
        cmd_parse_scores(args.critic_type, args.response_text, mode=args.mode)
    elif op == "should-refine":
        if not args.name:
            _error("--name required for should-refine", exit_code=2)
        cmd_should_refine(
            args.name,
            args.iteration,
            args.quality_threshold,
            args.criterion_floor,
            mode=args.mode,
        )
    elif op == "generate-feedback":
        if not args.name:
            _error("--name required for generate-feedback", exit_code=2)
        cmd_generate_feedback(args.name, args.iteration, mode=args.mode)
    elif op == "run-arc-analysis":
        if not args.name:
            _error("--name required for run-arc-analysis", exit_code=2)
        if not args.content:
            _error("--content required for run-arc-analysis", exit_code=2)
        cmd_run_arc_analysis(
            args.name,
            args.content,
            args.critic_summary,
            model=args.model,
        )


if __name__ == "__main__":
    main()
