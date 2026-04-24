import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]

_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from domain.exceptions import ConfigurationError


def test_load_agent_prompt_returns_body_without_frontmatter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import infrastructure.prompts.agent_prompt_loader as loader_module

    prompt_path = tmp_path / "test-agent.md"
    prompt_path.write_text(
        "---\ndescription: X\nmode: test\n---\n\n# My Prompt\nBody text",
        encoding="utf-8",
    )
    monkeypatch.setattr(loader_module, "AGENTS_DIR", tmp_path)

    try:
        result = loader_module.load_agent_prompt("test-agent")
        assert result == "# My Prompt\nBody text"
    finally:
        loader_module.clear_agent_prompt_cache()


def test_load_agent_prompt_without_frontmatter_returns_verbatim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import infrastructure.prompts.agent_prompt_loader as loader_module

    prompt_path = tmp_path / "test-agent.md"
    prompt_path.write_text("# My Prompt\nSome content", encoding="utf-8")
    monkeypatch.setattr(loader_module, "AGENTS_DIR", tmp_path)

    try:
        result = loader_module.load_agent_prompt("test-agent")
        assert result == "# My Prompt\nSome content"
    finally:
        loader_module.clear_agent_prompt_cache()


def test_load_agent_prompt_malformed_frontmatter_raises_value_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import infrastructure.prompts.agent_prompt_loader as loader_module

    prompt_path = tmp_path / "test-agent.md"
    prompt_path.write_text(
        "---\ndescription: X\nno closing delimiter\nand more content",
        encoding="utf-8",
    )
    monkeypatch.setattr(loader_module, "AGENTS_DIR", tmp_path)

    try:
        with pytest.raises(ValueError):
            loader_module.load_agent_prompt("test-agent")
    finally:
        loader_module.clear_agent_prompt_cache()


def test_load_agent_prompt_missing_file_raises_configuration_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import infrastructure.prompts.agent_prompt_loader as loader_module

    monkeypatch.setattr(loader_module, "AGENTS_DIR", tmp_path)

    try:
        with pytest.raises(ConfigurationError):
            loader_module.load_agent_prompt("nonexistent")
    finally:
        loader_module.clear_agent_prompt_cache()


def test_load_agent_prompt_caches_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import infrastructure.prompts.agent_prompt_loader as loader_module

    prompt_path = tmp_path / "test-agent.md"
    prompt_path.write_text("# My Prompt\nBody text", encoding="utf-8")
    monkeypatch.setattr(loader_module, "AGENTS_DIR", tmp_path)

    try:
        first = loader_module.load_agent_prompt("test-agent")
        second = loader_module.load_agent_prompt("test-agent")
        assert first is second or first == second
    finally:
        loader_module.clear_agent_prompt_cache()


def test_clear_agent_prompt_cache_clears_all_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import infrastructure.prompts.agent_prompt_loader as loader_module

    prompt_path = tmp_path / "test-agent.md"
    prompt_path.write_text("# My Prompt\nBody text", encoding="utf-8")
    monkeypatch.setattr(loader_module, "AGENTS_DIR", tmp_path)

    try:
        cached = loader_module.load_agent_prompt("test-agent")
        prompt_path.unlink()
        assert loader_module.load_agent_prompt("test-agent") == cached

        loader_module.clear_agent_prompt_cache()

        with pytest.raises(ConfigurationError):
            loader_module.load_agent_prompt("test-agent")
    finally:
        loader_module.clear_agent_prompt_cache()
