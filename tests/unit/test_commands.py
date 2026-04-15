"""Verification tests for Issue #21 — OpenCode Custom Commands.

Confirms that all 7 command files in .opencode/commands/ exist with valid
YAML frontmatter, correct agent routing, and expected body content.
"""

from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COMMANDS_DIR = PROJECT_ROOT / ".opencode" / "commands"

ALL_COMMANDS = [
    "new-story.md",
    "continue.md",
    "regenerate.md",
    "savepoint.md",
    "status.md",
    "settings.md",
    "wiki.md",
]

ORCHESTRATOR_COMMANDS = ["new-story.md", "continue.md", "regenerate.md", "savepoint.md"]
INFO_COMMANDS = ["status.md", "settings.md", "wiki.md"]


def _parse_command(filename: str) -> tuple[dict, str]:
    """Parse a command file into (frontmatter_dict, body_str)."""
    text = (COMMANDS_DIR / filename).read_text()
    parts = text.split("---", 2)
    frontmatter = yaml.safe_load(parts[1])
    body = parts[2] if len(parts) > 2 else ""
    return frontmatter, body


def test_all_command_files_exist():
    for name in ALL_COMMANDS:
        assert (COMMANDS_DIR / name).is_file(), f"Missing command file: {name}"


def test_command_frontmatter_valid():
    for name in ALL_COMMANDS:
        fm, _ = _parse_command(name)
        assert isinstance(fm, dict), f"{name}: frontmatter is not a dict"
        assert "description" in fm, f"{name}: missing 'description' field"


def test_command_descriptions_not_empty():
    for name in ALL_COMMANDS:
        fm, _ = _parse_command(name)
        assert fm["description"].strip(), f"{name}: description is empty"


def test_orchestrator_commands_have_agent():
    for name in ORCHESTRATOR_COMMANDS:
        fm, _ = _parse_command(name)
        assert fm.get("agent") == "story-orchestrator", (
            f"{name}: expected agent 'story-orchestrator', got {fm.get('agent')!r}"
        )


def test_info_commands_no_agent():
    for name in INFO_COMMANDS:
        fm, _ = _parse_command(name)
        assert "agent" not in fm, f"{name}: should not have 'agent' field"


def test_new_story_references_prompt_arg():
    _, body = _parse_command("new-story.md")
    assert "$1" in body, "new-story.md body should reference $1"


def test_regenerate_uses_arguments():
    _, body = _parse_command("regenerate.md")
    assert "$ARGUMENTS" in body, "regenerate.md body should reference $ARGUMENTS"


def test_continue_injects_story_list():
    _, body = _parse_command("continue.md")
    assert "!python3 src/tools/story_state.py --operation list" in body, (
        "continue.md should inject story list via shell command"
    )


def test_status_injects_shell_commands():
    _, body = _parse_command("status.md")
    assert "!python3" in body, "status.md should contain !python3 shell command"
    assert "!find" in body, "status.md should contain !find shell command"


def test_settings_includes_config():
    _, body = _parse_command("settings.md")
    assert "@config.md" in body, "settings.md should reference @config.md"


def test_wiki_runs_lint():
    _, body = _parse_command("wiki.md")
    assert "wiki_lint.py" in body, "wiki.md should reference wiki_lint.py"


def test_gitkeep_removed():
    assert not (COMMANDS_DIR / ".gitkeep").exists(), (
        ".gitkeep should not exist in .opencode/commands/"
    )
