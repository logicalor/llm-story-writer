"""Verification tests for outline-generator Tool.

Confirms the CLI tool (src/tools/outline_generator.py) correctly handles
error paths, input validation, the non-LLM generate-elements operation,
savepoint resumability, and numeric argument validation.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import src.tools.outline_generator as og

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOL_SCRIPT = str(PROJECT_ROOT / "src" / "tools" / "outline_generator.py")

# The 8 analysis chunk types (must match CHUNK_TYPES in outline_generator.py)
CHUNK_TYPES = (
    "core_story_foundation",
    "character_foundation",
    "setting_foundation",
    "plot_structure",
    "theme_message",
    "tone_style",
    "conflict_stakes",
    "world_rules_logic",
)


@pytest.fixture()
def story_env(tmp_path: Path) -> tuple[Path, str]:
    """Provide a temp stories directory with a pre-created story."""
    stories_dir = tmp_path / "stories"
    story_name = "test-story"
    (stories_dir / story_name / "savepoints").mkdir(parents=True)
    return stories_dir, story_name


def _run_tool(
    *args: str, stories_dir: Path | None = None
) -> subprocess.CompletedProcess[str]:
    env = {**os.environ}
    if stories_dir is not None:
        env["STORIES_DIR"] = str(stories_dir)
    return subprocess.run(
        [sys.executable, TOOL_SCRIPT, *args],
        capture_output=True,
        text=True,
        env=env,
    )


def _write_savepoint(
    stories_dir: Path, story_name: str, step_name: str, data: str
) -> None:
    """Write a string savepoint file directly (matches FilesystemSavepointRepository format)."""
    savepoint_dir = stories_dir / story_name / "savepoints"
    if "/" in step_name:
        parts = step_name.split("/")
        filename = parts[-1]
        subdirs = parts[:-1]
        target_dir = savepoint_dir
        for subdir in subdirs:
            target_dir = target_dir / subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        filepath = target_dir / f"{filename}.md"
    else:
        filepath = savepoint_dir / f"{step_name}.md"
    filepath.write_text(f"# Savepoint: {step_name}\n\n{data}", encoding="utf-8")


# ---------------------------------------------------------------------------
# Test: missing required arguments
# ---------------------------------------------------------------------------


def test_analyze_prompt_missing_name(story_env: tuple[Path, str]) -> None:
    """Call without --name exits with argparse error code 2."""
    stories_dir, _ = story_env
    result = _run_tool(
        "--operation",
        "analyze-prompt",
        "--prompt",
        "A story about dragons",
        stories_dir=stories_dir,
    )
    assert result.returncode == 2


def test_analyze_prompt_missing_prompt(story_env: tuple[Path, str]) -> None:
    """Call analyze-prompt without --prompt exits with code 2."""
    stories_dir, name = story_env
    result = _run_tool(
        "--operation",
        "analyze-prompt",
        "--name",
        name,
        stories_dir=stories_dir,
    )
    assert result.returncode == 2
    assert "prompt" in result.stderr.lower()


# ---------------------------------------------------------------------------
# Test: missing savepoints for dependent operations
# ---------------------------------------------------------------------------


def test_generate_elements_missing_savepoints(story_env: tuple[Path, str]) -> None:
    """generate-elements without analysis chunks exits 1 with missing chunk message."""
    stories_dir, name = story_env
    result = _run_tool(
        "--operation",
        "generate-elements",
        "--name",
        name,
        stories_dir=stories_dir,
    )
    assert result.returncode == 1
    assert "missing chunk savepoint" in result.stderr.lower()


def test_generate_outline_missing_savepoints(story_env: tuple[Path, str]) -> None:
    """generate-outline without story_elements exits 1."""
    stories_dir, name = story_env
    result = _run_tool(
        "--operation",
        "generate-outline",
        "--name",
        name,
        "--desired-chapters",
        "10",
        stories_dir=stories_dir,
    )
    assert result.returncode == 1
    assert "story_elements" in result.stderr.lower()


def test_expand_chapter_missing_savepoints(story_env: tuple[Path, str]) -> None:
    """expand-chapter without story_elements exits 1."""
    stories_dir, name = story_env
    result = _run_tool(
        "--operation",
        "expand-chapter",
        "--name",
        name,
        "--chunk-start",
        "1",
        "--chunk-end",
        "5",
        "--total-chapters",
        "20",
        stories_dir=stories_dir,
    )
    assert result.returncode == 1
    assert "story_elements" in result.stderr.lower()


def test_refine_missing_savepoints(story_env: tuple[Path, str]) -> None:
    """refine without initial_outline exits 1."""
    stories_dir, name = story_env
    result = _run_tool(
        "--operation",
        "refine",
        "--name",
        name,
        "--feedback",
        "Add more conflict",
        stories_dir=stories_dir,
    )
    assert result.returncode == 1
    assert "initial_outline" in result.stderr.lower()


# ---------------------------------------------------------------------------
# Test: generate-elements (non-LLM, fully testable)
# ---------------------------------------------------------------------------


def test_generate_elements_with_savepoints(story_env: tuple[Path, str]) -> None:
    """Pre-populate 8 chunk savepoints, call generate-elements, verify concatenated output."""
    stories_dir, name = story_env

    # Write all 8 chunk savepoints
    for chunk_type in CHUNK_TYPES:
        step = f"story_analysis/{chunk_type}_chunk"
        _write_savepoint(stories_dir, name, step, f"Content for {chunk_type} analysis.")

    result = _run_tool(
        "--operation",
        "generate-elements",
        "--name",
        name,
        stories_dir=stories_dir,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    out = json.loads(result.stdout)

    # Output returns savepoint key only (not full content) to avoid stdout bloat
    assert out["data"]["savepoint"] == "story_elements"


def test_generate_elements_output_format(story_env: tuple[Path, str]) -> None:
    """Verify output is valid JSON with status, operation, data keys."""
    stories_dir, name = story_env

    # Write all 8 chunk savepoints
    for chunk_type in CHUNK_TYPES:
        step = f"story_analysis/{chunk_type}_chunk"
        _write_savepoint(stories_dir, name, step, f"Chunk {chunk_type}")

    result = _run_tool(
        "--operation",
        "generate-elements",
        "--name",
        name,
        stories_dir=stories_dir,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    out = json.loads(result.stdout)
    assert "status" in out
    assert "operation" in out
    assert "data" in out
    assert out["status"] == "success"
    assert out["operation"] == "generate-elements"


# ---------------------------------------------------------------------------
# Test: input validation
# ---------------------------------------------------------------------------


def test_invalid_story_name_path_traversal(story_env: tuple[Path, str]) -> None:
    """Path traversal attempt (../evil) exits 1."""
    stories_dir, _ = story_env
    result = _run_tool(
        "--operation",
        "generate-elements",
        "--name",
        "../evil",
        stories_dir=stories_dir,
    )
    assert result.returncode == 1
    assert "escapes" in result.stderr.lower()


def test_invalid_operation(story_env: tuple[Path, str]) -> None:
    """Unknown operation exits 2 (argparse choices validation)."""
    stories_dir, name = story_env
    result = _run_tool(
        "--operation",
        "invalid",
        "--name",
        name,
        stories_dir=stories_dir,
    )
    assert result.returncode == 2


# ---------------------------------------------------------------------------
# Fixture: monkeypatched environment for direct function calls
# ---------------------------------------------------------------------------


@pytest.fixture()
def patched_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, str]:
    """Redirect STORIES_DIR and stub _load_prompt for direct function calls."""
    stories_dir = tmp_path / "stories"
    story_name = "test-story"
    (stories_dir / story_name / "savepoints").mkdir(parents=True)

    monkeypatch.setattr(og, "STORIES_DIR", stories_dir)
    monkeypatch.setattr(og, "_load_prompt", lambda *_a, **_kw: "mock prompt text")

    return stories_dir, story_name


# ---------------------------------------------------------------------------
# Test: analyze-prompt happy path (monkeypatched)
# ---------------------------------------------------------------------------


def test_analyze_prompt_happy_path(
    patched_env: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Monkeypatch LLM calls; verify all savepoints created by analyze-prompt."""
    stories_dir, name = patched_env

    call_count: dict[str, int] = {"llm": 0, "messages": 0}

    def fake_call_llm(prompt: str, *, model: str | None = None) -> str:
        call_count["llm"] += 1
        return "Fake LLM single response"

    def fake_call_llm_messages(
        messages: list[dict[str, str]], *, model: str | None = None
    ) -> str:
        call_count["messages"] += 1
        return f"Fake LLM message response #{call_count['messages']}"

    monkeypatch.setattr(og, "_call_llm", fake_call_llm)
    monkeypatch.setattr(og, "_call_llm_messages", fake_call_llm_messages)

    og.cmd_analyze_prompt(name, "Write a story about dragons", model="test-model")

    repo = og._make_repo(name)
    # understand_prompt savepoint
    assert og._has_savepoint(repo, "understand_prompt")
    # 8 analysis chunk savepoints
    for chunk_type in CHUNK_TYPES:
        assert og._has_savepoint(repo, f"story_analysis/{chunk_type}_chunk")
    # story_start_date and base_context
    assert og._has_savepoint(repo, "story_start_date")
    assert og._has_savepoint(repo, "base_context")

    # Verify success JSON on stdout
    captured = capsys.readouterr()
    out = json.loads(captured.out)
    assert out["status"] == "success"
    assert out["operation"] == "analyze-prompt"
    assert out["data"]["chunks_generated"] == 8


# ---------------------------------------------------------------------------
# Test: generate-outline happy path (monkeypatched)
# ---------------------------------------------------------------------------


def test_generate_outline_happy_path(
    patched_env: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Pre-populate prerequisites; verify initial_outline savepoint created."""
    stories_dir, name = patched_env

    # Pre-populate required savepoints
    _write_savepoint(stories_dir, name, "story_elements", "Elements content")
    _write_savepoint(stories_dir, name, "base_context", "Base context content")

    def fake_call_llm(prompt: str, *, model: str | None = None) -> str:
        return "Chapter 1: The Beginning\nChapter 2: The Middle"

    monkeypatch.setattr(og, "_call_llm", fake_call_llm)

    og.cmd_generate_outline(
        name, 10, prompt="Write a story about dragons", model="test-model"
    )

    repo = og._make_repo(name)
    assert og._has_savepoint(repo, "initial_outline")

    captured = capsys.readouterr()
    out = json.loads(captured.out)
    assert out["status"] == "success"
    assert out["operation"] == "generate-outline"
    assert "outline" in out["data"]


# ---------------------------------------------------------------------------
# Test: generate-outline resumable (cached savepoint skips LLM)
# ---------------------------------------------------------------------------


def test_generate_outline_resumable(
    patched_env: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Pre-populate initial_outline; LLM should NOT be called."""
    stories_dir, name = patched_env

    _write_savepoint(stories_dir, name, "story_elements", "Elements content")
    _write_savepoint(stories_dir, name, "base_context", "Base context content")
    _write_savepoint(stories_dir, name, "initial_outline", "Cached outline")

    def llm_should_not_be_called(prompt: str, *, model: str | None = None) -> str:
        raise AssertionError("_call_llm should not be called when savepoint exists")

    monkeypatch.setattr(og, "_call_llm", llm_should_not_be_called)

    og.cmd_generate_outline(
        name, 10, prompt="Write a story about dragons", model="test-model"
    )

    captured = capsys.readouterr()
    out = json.loads(captured.out)
    assert out["status"] == "success"
    assert "Cached outline" in out["data"]["outline"]


# ---------------------------------------------------------------------------
# Test: expand-chapter happy path (monkeypatched)
# ---------------------------------------------------------------------------


def test_expand_chapter_happy_path(
    patched_env: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Pre-populate prerequisites; verify outline_chunk and continuity savepoints."""
    stories_dir, name = patched_env

    _write_savepoint(stories_dir, name, "story_elements", "Elements content")
    _write_savepoint(stories_dir, name, "base_context", "Base context content")

    call_count = 0

    def fake_call_llm(prompt: str, *, model: str | None = None) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return "Expanded chapters 1-3 outline"
        return "Continuity analysis for chapters 1-3"

    monkeypatch.setattr(og, "_call_llm", fake_call_llm)

    og.cmd_expand_chapter(name, 1, 3, 10, model="test-model")

    repo = og._make_repo(name)
    assert og._has_savepoint(repo, "outline_chunk_1_3")
    assert og._has_savepoint(repo, "continuity_1_3")

    captured = capsys.readouterr()
    out = json.loads(captured.out)
    assert out["status"] == "success"
    assert out["operation"] == "expand-chapter"
    assert "chunk_outline" in out["data"]
    assert "continuity_analysis" in out["data"]


# ---------------------------------------------------------------------------
# Test: expand-chapter resumable (cached savepoints skip LLM)
# ---------------------------------------------------------------------------


def test_expand_chapter_resumable(
    patched_env: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Pre-populate chunk + continuity savepoints; LLM should NOT be called."""
    stories_dir, name = patched_env

    _write_savepoint(stories_dir, name, "story_elements", "Elements content")
    _write_savepoint(stories_dir, name, "base_context", "Base context content")
    _write_savepoint(stories_dir, name, "outline_chunk_1_3", "Cached chunk")
    _write_savepoint(stories_dir, name, "continuity_1_3", "Cached continuity")

    def llm_should_not_be_called(prompt: str, *, model: str | None = None) -> str:
        raise AssertionError("_call_llm should not be called when savepoints exist")

    monkeypatch.setattr(og, "_call_llm", llm_should_not_be_called)

    og.cmd_expand_chapter(name, 1, 3, 10, model="test-model")

    captured = capsys.readouterr()
    out = json.loads(captured.out)
    assert out["status"] == "success"
    assert "Cached chunk" in out["data"]["chunk_outline"]
    assert "Cached continuity" in out["data"]["continuity_analysis"]


# ---------------------------------------------------------------------------
# Test: refine happy path (monkeypatched)
# ---------------------------------------------------------------------------


def test_refine_happy_path(
    patched_env: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Pre-populate prerequisites; verify refined_outline savepoint and feedback included."""
    stories_dir, name = patched_env

    _write_savepoint(stories_dir, name, "initial_outline", "Original outline")
    _write_savepoint(stories_dir, name, "story_elements", "Elements content")
    _write_savepoint(stories_dir, name, "base_context", "Base context content")

    received_prompts: list[str] = []

    def fake_call_llm(prompt: str, *, model: str | None = None) -> str:
        received_prompts.append(prompt)
        return "Refined outline with stronger ending"

    monkeypatch.setattr(og, "_call_llm", fake_call_llm)

    og.cmd_refine(name, "Make the ending stronger", model="test-model")

    repo = og._make_repo(name)
    assert og._has_savepoint(repo, "refined_outline")

    # Verify feedback was incorporated into the prompt
    assert len(received_prompts) == 1
    assert "Make the ending stronger" in received_prompts[0]

    captured = capsys.readouterr()
    out = json.loads(captured.out)
    assert out["status"] == "success"
    assert out["operation"] == "refine"
    assert "Refined outline with stronger ending" in out["data"]["refined_outline"]


# ---------------------------------------------------------------------------
# Test: numeric argument validation (subprocess, matching existing pattern)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "extra_args,expected_err",
    [
        # --desired-chapters must be >= 1
        (
            ["--operation", "generate-outline", "--desired-chapters", "0"],
            "desired-chapters must be >= 1",
        ),
        # --chunk-start must be >= 1
        (
            [
                "--operation",
                "expand-chapter",
                "--chunk-start",
                "0",
                "--chunk-end",
                "3",
                "--total-chapters",
                "10",
            ],
            "chunk-start must be >= 1",
        ),
        # --chunk-end must be >= --chunk-start
        (
            [
                "--operation",
                "expand-chapter",
                "--chunk-start",
                "5",
                "--chunk-end",
                "3",
                "--total-chapters",
                "10",
            ],
            "chunk-end must be >= --chunk-start",
        ),
        # --total-chapters must be >= --chunk-end
        (
            [
                "--operation",
                "expand-chapter",
                "--chunk-start",
                "1",
                "--chunk-end",
                "5",
                "--total-chapters",
                "3",
            ],
            "total-chapters must be >= --chunk-end",
        ),
    ],
    ids=[
        "desired_chapters_zero",
        "chunk_start_zero",
        "chunk_end_lt_start",
        "total_lt_chunk_end",
    ],
)
def test_numeric_validation_errors(
    story_env: tuple[Path, str],
    extra_args: list[str],
    expected_err: str,
) -> None:
    """Numeric boundary violations exit with error containing expected message."""
    stories_dir, name = story_env
    result = _run_tool(
        *extra_args,
        "--name",
        name,
        stories_dir=stories_dir,
    )
    assert result.returncode == 1
    assert expected_err in result.stderr
