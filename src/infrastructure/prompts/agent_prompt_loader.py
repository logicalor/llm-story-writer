"""Loader for agent system prompt files."""

from pathlib import Path

from domain.exceptions import ConfigurationError

AGENTS_DIR: Path = Path(__file__).resolve().parents[3] / "prompts" / "agents"

_cache: dict[str, str] = {}


def load_agent_prompt(name: str) -> str:
    """Load and return an agent system prompt, stripping YAML frontmatter.

    Results are cached in-memory for the lifetime of the process.

    Args:
        name: Agent file stem (e.g. "story-orchestrator").

    Returns:
        The prompt body with frontmatter removed.

    Raises:
        ConfigurationError: If the file does not exist.
        ValueError: If the frontmatter is malformed (opening --- with no closing ---).
    """
    if "/" in name or "\\" in name or name.startswith("."):
        raise ValueError(f"Invalid agent name: {name!r}")

    if name in _cache:
        return _cache[name]

    file_path = AGENTS_DIR / f"{name}.md"
    if not file_path.exists():
        raise ConfigurationError(f"Agent prompt file not found: {file_path}")

    content = file_path.read_text(encoding="utf-8")

    if content.startswith("---\n"):
        closing = content.find("---\n", 4)
        if closing == -1:
            raise ValueError(
                f"Malformed frontmatter in agent prompt '{name}': missing closing '---'"
            )
        body = content[closing + 4 :].strip()
    else:
        body = content.strip()

    _cache[name] = body
    return body


def clear_agent_prompt_cache() -> None:
    """Clear the in-memory agent prompt cache."""
    _cache.clear()
