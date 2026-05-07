"""CLI tool for persona generation and view extraction."""

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

from tools._io import STORIES_DIR, _validate_story_name  # noqa: E402

REQUIRED_SECTIONS = [
    "## Identity",
    "## Prose Texture",
    "## Dialogue Style",
    "## Pacing Philosophy",
    "## Thematic Sensibility",
    "## Narrative Philosophy",
    "## Anti-Patterns",
]
VALID_VIEWS = {"outline", "chapter", "scrubber", "editor"}

_FRONTMATTER_RE = re.compile(r"\A---\s*\n.*?\n---\s*\n?", re.DOTALL)
_SECTION_RE = re.compile(r"^(## [^\n]+)\n(.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


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
    from tools._llm import generate_text

    return generate_text(prompt, model=model)


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


def _validate_persona_doc(text: str) -> list[str]:
    """Return persona document validation errors."""
    errors: list[str] = []
    if not text.startswith("---"):
        errors.append("Missing YAML frontmatter at document start")
    for heading in REQUIRED_SECTIONS:
        if heading not in text:
            errors.append(f"Missing required section: {heading}")
    return errors


def _strip_frontmatter(text: str) -> str:
    """Strip YAML frontmatter from the top of a document."""
    return _FRONTMATTER_RE.sub("", text, count=1).strip()


def _extract_sections(body: str) -> dict[str, str]:
    """Extract level-two sections from a markdown body."""
    sections: dict[str, str] = {}
    for heading, content in _SECTION_RE.findall(body):
        sections[heading] = content.strip()
    return sections


def _get_persona_dir(name: str) -> Path:
    """Return the persona directory for a story."""
    story_dir = _validate_story_name(name, base_dir=STORIES_DIR)
    persona_dir = story_dir / "persona"
    persona_dir.mkdir(parents=True, exist_ok=True)
    return persona_dir


def cmd_generate(
    name: str, *, model: str | None = None, word_budget: int = 225
) -> None:
    """Generate a persona document from outline analysis savepoints."""
    from datetime import datetime, timezone

    word_budget = max(100, min(500, word_budget))
    repo = _make_repo(name)

    savepoint_data: dict[str, str] = {}
    for step_name in (
        "core_story_foundation",
        "tone_style",
        "theme_message",
        "story_elements",
    ):
        data = _load_savepoint(repo, step_name)
        if data is None or data == "":
            _error(
                f"Missing required savepoint: {step_name}. Run outline analysis first."
            )
        if isinstance(data, str):
            savepoint_data[step_name] = data
        else:
            savepoint_data[step_name] = json.dumps(data, default=str)

    prompt = _load_prompt(
        "persona/generate",
        {
            "word_budget": word_budget,
            "core_story_foundation": savepoint_data["core_story_foundation"],
            "tone_style": savepoint_data["tone_style"],
            "theme_message": savepoint_data["theme_message"],
            "story_elements": savepoint_data["story_elements"],
        },
    )
    response = _call_llm(prompt, model=model)
    errors = _validate_persona_doc(response)

    if errors:
        persona_dir = _get_persona_dir(name)
        failed_path = persona_dir / ".last-failed.md"
        failed_path.write_text(response, encoding="utf-8")
        _error(
            "persona/validate",
            data={"errors": errors, "last_failed_path": str(failed_path)},
        )

    persona_dir = _get_persona_dir(name)
    persona_path = persona_dir / "persona.md"
    persona_path.write_text(response, encoding="utf-8")
    ts = datetime.now(timezone.utc).isoformat()
    _save_savepoint(
        repo,
        "persona",
        {
            "persona_path": str(persona_path),
            "generation_timestamp": ts,
        },
    )
    word_count = len(response.split())
    _success(
        "generate",
        {
            "persona_path": str(persona_path),
            "savepoint_step": "persona",
            "word_count": word_count,
        },
    )


def cmd_get_view(name: str, view: str) -> None:
    """Print a persona view for downstream tools."""
    if view not in VALID_VIEWS:
        print(
            json.dumps(
                {
                    "status": "error",
                    "operation": "get-view",
                    "data": {
                        "message": f"Invalid view: {view!r}. Valid views: {sorted(VALID_VIEWS)}"
                    },
                },
                indent=2,
            )
        )
        sys.exit(1)

    story_dir = _validate_story_name(name, base_dir=STORIES_DIR)
    persona_path = story_dir / "persona" / "persona.md"
    if not persona_path.exists():
        sys.exit(0)

    text = persona_path.read_text(encoding="utf-8")
    body = _strip_frontmatter(text)
    sections = _extract_sections(body)

    if view == "chapter":
        output = body
    elif view == "outline":
        parts = []
        for heading in [
            "## Identity",
            "## Narrative Philosophy",
            "## Thematic Sensibility",
            "## Pacing Philosophy",
            "## Anti-Patterns",
        ]:
            if heading in sections:
                parts.append(f"{heading}\n{sections[heading]}")
        output = "\n\n".join(parts)
    elif view == "scrubber":
        identity_content = sections.get("## Identity", "")
        sentences = _SENTENCE_SPLIT_RE.split(identity_content.strip(), maxsplit=1)
        first_sentence = (
            sentences[0].strip() if sentences and sentences[0].strip() else ""
        )
        if first_sentence and not first_sentence.endswith("."):
            first_sentence += "."
        parts = [f"## Identity\n{first_sentence}"]
        for heading in ["## Prose Texture", "## Dialogue Style", "## Anti-Patterns"]:
            if heading in sections:
                parts.append(f"{heading}\n{sections[heading]}")
        output = "\n\n".join(parts)
    else:
        parts = []
        for heading in [
            "## Identity",
            "## Prose Texture",
            "## Dialogue Style",
            "## Narrative Philosophy",
            "## Anti-Patterns",
        ]:
            if heading in sections:
                parts.append(f"{heading}\n{sections[heading]}")
        output = "\n\n".join(parts)

    print(output)


def cmd_regenerate(
    name: str, *, model: str | None = None, word_budget: int = 225
) -> None:
    """Archive the current persona and generate a fresh one."""
    from datetime import datetime, timezone

    story_dir = _validate_story_name(name, base_dir=STORIES_DIR)
    persona_path = story_dir / "persona" / "persona.md"
    if persona_path.exists():
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        history_dir = persona_path.parent / "history"
        history_dir.mkdir(parents=True, exist_ok=True)
        archive_path = history_dir / f"persona-{ts}.md"
        archive_path.write_text(
            persona_path.read_text(encoding="utf-8"), encoding="utf-8"
        )

    cmd_generate(name, model=model, word_budget=word_budget)


def main() -> None:
    """Run the persona builder CLI."""
    parser = argparse.ArgumentParser(
        description="Persona builder: generate, get-view, regenerate"
    )
    parser.add_argument(
        "--operation", required=True, choices=["generate", "get-view", "regenerate"]
    )
    parser.add_argument("--name", required=True, help="Story name")
    parser.add_argument("--model", default=None, help="LLM model override")
    parser.add_argument("--word-budget", type=int, default=225, dest="word_budget")
    parser.add_argument("--view", default=None, help="View type for get-view")
    args = parser.parse_args()

    op = args.operation
    if op == "generate":
        cmd_generate(args.name, model=args.model, word_budget=args.word_budget)
    elif op == "get-view":
        view = args.view or ""
        cmd_get_view(args.name, view)
    elif op == "regenerate":
        cmd_regenerate(args.name, model=args.model, word_budget=args.word_budget)


if __name__ == "__main__":
    main()
