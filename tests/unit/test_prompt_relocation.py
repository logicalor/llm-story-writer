"""Verification tests for Issue #5 — Prompt Template Relocation.

Confirms that 131 prompt templates were correctly moved from
src/application/strategies/outline_chapter/prompts/ to the top-level prompts/ directory,
and that all code references point to the new location.
"""

import inspect
import sys
from pathlib import Path

# Project root is two directories above this test file (tests/unit/)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# src/ must be on sys.path so bare imports (e.g. "from domain.exceptions ...")
# used inside the production modules resolve correctly.
_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)


def test_prompts_directory_exists():
    """Verify prompts/ directory exists at project root."""
    prompts_dir = PROJECT_ROOT / "prompts"
    assert prompts_dir.is_dir(), f"Expected prompts/ directory at {prompts_dir}"


def test_no_prompts_in_old_location():
    """Verify src/application/strategies/outline_chapter/prompts/ does NOT exist."""
    old_dir = (
        PROJECT_ROOT
        / "src"
        / "application"
        / "strategies"
        / "outline_chapter"
        / "prompts"
    )
    assert not old_dir.exists(), f"Old prompts directory still exists at {old_dir}"


def test_prompt_subdirectories_exist():
    """Verify all expected subdirectories exist under prompts/."""
    prompts_dir = PROJECT_ROOT / "prompts"
    expected_subdirs = [
        "chapters",
        "characters",
        "multistep",
        "outline",
        "outline_review",
        "recap",
        "scenes",
        "settings",
        "story_state",
        "_unused",
    ]
    for subdir in expected_subdirs:
        path = prompts_dir / subdir
        assert path.is_dir(), f"Expected subdirectory {subdir}/ under prompts/"


def test_root_level_prompts_exist():
    """Verify the 3 root-level prompt files exist."""
    prompts_dir = PROJECT_ROOT / "prompts"
    expected_files = [
        "extract_base_context.md",
        "extract_chapter_events.md",
        "extract_story_start_date.md",
    ]
    for filename in expected_files:
        path = prompts_dir / filename
        assert path.is_file(), f"Expected root-level prompt {filename} in prompts/"


def test_prompt_loader_default_path():
    """Import PromptLoader and verify its default __init__ parameter is 'prompts'."""
    from infrastructure.prompts.prompt_loader import PromptLoader

    sig = inspect.signature(PromptLoader.__init__)
    default = sig.parameters["prompts_dir"].default
    assert default == "prompts", (
        f"PromptLoader default prompts_dir should be 'prompts', got '{default}'"
    )


def test_outline_chapter_prompt_directory():
    """Verify OutlineChapterStrategy.get_prompt_directory() returns 'prompts'.

    Parses the source file directly to avoid importing heavy transitive
    dependencies (aiohttp, etc.) that may not be installed in the test env.
    """
    strategy_file = (
        PROJECT_ROOT
        / "src"
        / "application"
        / "strategies"
        / "outline_chapter"
        / "strategy.py"
    )
    assert strategy_file.is_file(), f"Strategy file not found: {strategy_file}"
    source = strategy_file.read_text(encoding="utf-8")
    # The method should contain: return "prompts"
    assert 'return "prompts"' in source, (
        'get_prompt_directory() should return "prompts" but pattern not found in source'
    )


def test_prompt_file_count():
    """Count all .md files under prompts/ and verify there are 142."""
    prompts_dir = PROJECT_ROOT / "prompts"
    md_files = list(prompts_dir.rglob("*.md"))
    assert len(md_files) == 142, (
        f"Expected 142 .md files under prompts/, found {len(md_files)}"
    )
