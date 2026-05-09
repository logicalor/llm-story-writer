"""Repository invariants for live generation settings and prompt assets."""

import dataclasses
from pathlib import Path
import subprocess

from src.domain.value_objects.generation_settings import GenerationSettings


NON_RUNTIME_PROMPT_PARTS = {"agents", "_unused", "skills"}
NON_RUNTIME_PROMPT_FILES = {
    Path("prompts/sample-story.md"),  # user-facing example, not a tool prompt template
    Path("prompts/chapters/create_list.md"),
    Path("prompts/chapters/create_list_iterative.md"),
    Path("prompts/multistep/outline/enrichment/understand_character_summaries.md"),
    Path("prompts/multistep/outline/enrichment/understand_setting_summaries.md"),
    Path("prompts/multistep/outline/enrichment/understand_story_elements.md"),
}

# Prompts loaded via f-string interpolation. The grep test cannot find their
# stems literally; instead we verify that the loader prefix appears in src/.
DYNAMIC_PROMPT_PATTERNS: tuple[tuple[str, str], ...] = (
    # (path-glob relative to repo root, src/ grep pattern proving the loader exists)
    ("prompts/multistep/outline/create_*_chunk.md", "multistep/outline/create_"),
    ("prompts/wiki/extract_*_from_chapter.md", "wiki/extract_"),
)

INTENTIONAL_CONFIG_SURFACE_SETTINGS = {
    # Declared and documented config surface for planned/partially migrated
    # features. These are validated and serialised by GenerationSettings, but
    # not yet read by runtime code paths.
    "enable_author_persona",
    "persona_model",
    "persona_word_budget",
    "enable_emphasis_delta",
}


def _grep_has_output(search_term: str, search_root: Path, *extra_args: str) -> bool:
    result = subprocess.run(
        [
            "grep",
            "-R",
            search_term,
            str(search_root),
            "--include=*.py",
            *extra_args,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return bool(result.stdout.strip())


def _is_runtime_prompt(prompt_path: Path) -> bool:
    if any(part in NON_RUNTIME_PROMPT_PARTS for part in prompt_path.parts):
        return False

    if prompt_path.name == "README.md":
        return False

    if prompt_path in NON_RUNTIME_PROMPT_FILES:
        return False

    return True


def _is_dynamically_loaded(prompt_path: Path) -> bool:
    for path_glob, src_pattern in DYNAMIC_PROMPT_PATTERNS:
        if prompt_path.match(path_glob) and _grep_has_output(src_pattern, Path("src")):
            return True

    return False


def test_no_dead_generation_settings():
    """Every field on GenerationSettings is referenced in src/ outside the dataclass file."""
    dead_fields = []

    for field in dataclasses.fields(GenerationSettings):
        if field.name in INTENTIONAL_CONFIG_SURFACE_SETTINGS:
            continue

        if not _grep_has_output(
            field.name,
            Path("src"),
            "--exclude=generation_settings.py",
        ):
            dead_fields.append(field.name)

    assert not dead_fields, (
        f"Dead GenerationSettings fields with no external call site: {dead_fields}"
    )


def test_no_orphan_prompts():
    """Every live runtime prompt under prompts/ has at least one call site in src/."""
    orphans = []

    for prompt_path in Path("prompts").rglob("*.md"):
        if not _is_runtime_prompt(prompt_path):
            continue

        if _is_dynamically_loaded(prompt_path):
            continue

        if not _grep_has_output(prompt_path.stem, Path("src")):
            orphans.append(str(prompt_path))

    assert not orphans, f"Prompt files with no call site in src/: {orphans}"
