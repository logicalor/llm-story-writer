"""Verification tests for Issue #3 — prompt-loader Tool.

Confirms the CLI tool (src/tools/prompt_loader.py) and the underlying
PromptLoader class correctly load, render, and validate prompt templates.
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

TOOL_SCRIPT = str(PROJECT_ROOT / "src" / "tools" / "prompt_loader.py")


def test_load_prompt_with_variables():
    """CLI: prompt with variables substitutes values correctly."""
    result = subprocess.run(
        [
            sys.executable,
            TOOL_SCRIPT,
            "--prompt-id",
            "chapters/create_content",
            "--variables",
            '{"chapter_num": "1"}',
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Expected exit 0, got {result.returncode}: {result.stderr}"
    )
    assert "chapter 1" in result.stdout.lower(), (
        f"Expected 'chapter 1' in output, got: {result.stdout[:200]}"
    )


def test_load_prompt_without_variables():
    """CLI: root-level prompt loads successfully without variables."""
    result = subprocess.run(
        [
            sys.executable,
            TOOL_SCRIPT,
            "--prompt-id",
            "extract_base_context",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Expected exit 0, got {result.returncode}: {result.stderr}"
    )
    assert len(result.stdout.strip()) > 0, "Expected non-empty output"


def test_missing_prompt_returns_error():
    """CLI: nonexistent prompt ID returns exit 1 with 'not found' in stderr."""
    result = subprocess.run(
        [
            sys.executable,
            TOOL_SCRIPT,
            "--prompt-id",
            "nonexistent/prompt",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1, f"Expected exit 1, got {result.returncode}"
    assert "not found" in result.stderr.lower(), (
        f"Expected 'not found' in stderr, got: {result.stderr}"
    )


def test_invalid_json_variables_returns_error():
    """CLI: malformed JSON in --variables returns exit 1 with 'Invalid JSON'."""
    result = subprocess.run(
        [
            sys.executable,
            TOOL_SCRIPT,
            "--prompt-id",
            "chapters/create_content",
            "--variables",
            "invalid json",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1, f"Expected exit 1, got {result.returncode}"
    assert "Invalid JSON" in result.stderr, (
        f"Expected 'Invalid JSON' in stderr, got: {result.stderr}"
    )


def test_prompt_loader_class_direct():
    """Direct: PromptLoader class loads and substitutes variables."""
    from infrastructure.prompts.prompt_loader import PromptLoader

    prompts_dir = str(PROJECT_ROOT / "prompts")
    loader = PromptLoader(prompts_dir=prompts_dir)
    result = loader.load_prompt("chapters/create_content", {"chapter_num": "1"})
    assert "chapter 1" in result.lower(), (
        f"Expected 'chapter 1' in rendered prompt, got: {result[:200]}"
    )


def test_missing_prompt_id_argument():
    """CLI: omitting --prompt-id returns exit 2 (argparse error)."""
    result = subprocess.run(
        [sys.executable, TOOL_SCRIPT],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2, f"Expected exit 2, got {result.returncode}"
