"""Verification tests for issue #5 (Prompt Template Relocation) and issue #164 (OpenCode artefact removal)."""

import inspect
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)


# --- Issue #5: Prompt Template Relocation ---


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
        "agents",
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


def test_prompt_file_count():
    """Count all .md files under prompts/ and verify relocation preserved the baseline set."""
    prompts_dir = PROJECT_ROOT / "prompts"
    md_files = list(prompts_dir.rglob("*.md"))
    assert len(md_files) >= 148, (
        f"Expected at least 148 .md files under prompts/, found {len(md_files)}"
    )


def test_agent_prompt_files_present():
    """Verify all expected agent prompt files exist under prompts/agents/."""
    agents_dir = PROJECT_ROOT / "prompts" / "agents"
    expected_files = [
        "chapter-outline-expander.md",
        "chapter-writer.md",
        "character-sheet-generator.md",
        "consistency-checker.md",
        "final-editor.md",
        "outline-planner.md",
        "prose-scrubber.md",
        "quality-reviewer.md",
        "story-orchestrator.md",
        "story-planner.md",
        "wiki-maintainer.md",
    ]
    for filename in expected_files:
        path = agents_dir / filename
        assert path.is_file(), f"Expected agent prompt {filename} in prompts/agents/"


# --- Issue #164: Stale Node.js build artefact removal ---


def test_stale_nodejs_build_artefacts_deleted() -> None:
    assert not (PROJECT_ROOT / "package.json").exists()
    assert not (PROJECT_ROOT / "package-lock.json").exists()
    assert not (PROJECT_ROOT / "tsconfig.json").exists()
    assert not (PROJECT_ROOT / "vitest.config.ts").exists()


def test_opencode_development_files_exist() -> None:
    assert (PROJECT_ROOT / ".opencode").is_dir()
    assert (PROJECT_ROOT / "opencode.json").is_file()


def test_commands_relocated_to_prompts_agents() -> None:
    assert (PROJECT_ROOT / "prompts" / "agents" / "continue.md").is_file()
    assert (PROJECT_ROOT / "prompts" / "agents" / "regenerate.md").is_file()


def test_skills_relocated_to_prompts_skills() -> None:
    skills_dir = PROJECT_ROOT / "prompts" / "skills"
    expected_skill_files = [
        "character-voice/SKILL.md",
        "context-budgeting/SKILL.md",
        "final-edit/SKILL.md",
        "narrative-arc/SKILL.md",
        "outline-structure/SKILL.md",
        "scene-writing/SKILL.md",
        "story-pipeline/SKILL.md",
        "wiki-conventions/SKILL.md",
        "wiki-maintenance/SKILL.md",
    ]

    assert skills_dir.is_dir()
    for relative_path in expected_skill_files:
        assert (skills_dir / relative_path).is_file()


def test_pyproject_has_required_dependencies() -> None:
    pyproject_text = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "textual>=6.0,<7.0" in pyproject_text
    assert "openai>=1.0" in pyproject_text


def test_pyproject_has_textual_version() -> None:
    pyproject_text = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "textual>=0.85.0,<1.0.0" not in pyproject_text


def test_no_stale_opencode_refs_in_agent_prompts() -> None:
    """Verify no agent prompt file references the deleted .opencode/ path."""
    agents_dir = PROJECT_ROOT / "prompts" / "agents"
    stale_refs = []
    for md_file in agents_dir.glob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        if ".opencode/" in content:
            stale_refs.append(md_file.name)
    assert not stale_refs, (
        f"Agent prompts contain stale .opencode/ references: {stale_refs}. "
        "Update these files to use prompts/skills/ paths instead."
    )
