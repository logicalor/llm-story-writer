"""End-to-end integration test: headless pipeline against LM Studio.

Requires a running LM Studio instance at http://127.0.0.1:1234/v1.
Auto-skips when LM Studio is not running.

Run with:
    pytest tests/integration/test_end_to_end_headless.py -v -m integration
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from collections.abc import Generator
from pathlib import Path

import httpx
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STORIES_DIR = PROJECT_ROOT / "stories"
STORY_NAME = "e2e-test"
STORY_DIR = STORIES_DIR / "e2e-test"
STORY_PROMPT = "A two-chapter short story about a robot learning to dream."
LM_STUDIO_URL = "http://127.0.0.1:1234/v1"
TIMEOUT_SECONDS = 600  # 10 minutes


def _tail_timeout_output(output: bytes | str | None) -> str:
    if output is None:
        return ""
    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")[-2000:]
    return output[-2000:]


@pytest.fixture(autouse=True)
def require_lm_studio() -> None:
    """Skip test if LM Studio is not running."""
    try:
        response = httpx.get(f"{LM_STUDIO_URL}/models", timeout=3)
    except (httpx.ConnectError, httpx.TimeoutException):
        pytest.skip("LM Studio not running - skipping integration test")
    if response.status_code != 200:
        pytest.skip("LM Studio not responding correctly - skipping integration test")


@pytest.fixture()
def e2e_story_dir() -> Generator[Path, None, None]:
    """Create the story fixture dir, yield it, then always clean up."""
    STORY_DIR.mkdir(parents=True, exist_ok=True)
    state_path = STORY_DIR / "state.json"
    state_path.write_text(json.dumps({"story_prompt": STORY_PROMPT}), encoding="utf-8")
    try:
        yield STORY_DIR
    finally:
        if STORY_DIR.exists():
            shutil.rmtree(STORY_DIR)


@pytest.mark.integration
@pytest.mark.slow
def test_two_chapter_story_batch(e2e_story_dir: Path) -> None:
    """Full headless pipeline produces a two-chapter story within the time budget."""
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.presentation.cli.main",
                "run",
                "--story",
                STORY_NAME,
                "--batch",
            ],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        pytest.fail(
            f"Pipeline timed out after {TIMEOUT_SECONDS}s.\n"
            f"stdout: {_tail_timeout_output(exc.stdout)}\n"
            f"stderr: {_tail_timeout_output(exc.stderr)}"
        )

    assert result.returncode == 0, (
        f"Pipeline exited with code {result.returncode}.\n"
        f"stdout: {result.stdout[-2000:]}\n"
        f"stderr: {result.stderr[-2000:]}"
    )

    savepoints_dir = e2e_story_dir / "savepoints"
    assert savepoints_dir.exists(), "Savepoints directory was not created"
    savepoint_files = list(savepoints_dir.iterdir())
    assert len(savepoint_files) > 0, "Savepoints directory is empty"

    pipeline_state_path = savepoints_dir / "pipeline_state.json"
    assert pipeline_state_path.exists(), "pipeline_state.json was not created"

    state_data = json.loads(pipeline_state_path.read_text(encoding="utf-8"))
    approved_chapters = state_data.get("approved_chapters", [])
    assert len(approved_chapters) >= 2, (
        f"Expected >= 2 approved chapters, got {len(approved_chapters)}"
    )

    chapter_heading_count = sum(
        1 for ch in approved_chapters if "Chapter" in ch.get("title", "")
    )
    assert chapter_heading_count >= 2, (
        f"Expected >= 2 chapters with 'Chapter' in title, got {chapter_heading_count}. "
        f"Titles: {[ch.get('title') for ch in approved_chapters]}"
    )

    for i, ch in enumerate(approved_chapters):
        assert ch.get("content", "").strip(), f"Chapter {i + 1} has empty content"
