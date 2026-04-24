"""Verification tests for Issue #164 — Python-native migration cleanup."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent


def test_opencode_artefacts_deleted() -> None:
    assert not (PROJECT_ROOT / ".opencode").exists()
    assert not (PROJECT_ROOT / "opencode.json").exists()
    assert not (PROJECT_ROOT / "package.json").exists()
    assert not (PROJECT_ROOT / "package-lock.json").exists()
    assert not (PROJECT_ROOT / "tsconfig.json").exists()
    assert not (PROJECT_ROOT / "vitest.config.ts").exists()


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

    assert 'textual>=6.0,<7.0' in pyproject_text
    assert 'openai>=1.0' in pyproject_text


def test_requirements_txt_textual_version() -> None:
    requirements_text = (PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8")

    assert 'textual>=6.0,<7.0' in requirements_text
    assert 'textual>=0.85.0,<1.0.0' not in requirements_text
