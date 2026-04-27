== REVIEW PACKAGE ==

=== BRANCH ===
feat/issue-212-headless-e2e-wiki

=== COMMIT LOG ===
41c5530 docs: update story-orchestrator and integration-tests for wiki E2E assertions (#212)
5c6d382 test(integration): strengthen headless E2E with wiki artifact assertions (#212)

=== CHANGED FILES ===
.github/notes/plans/issue-212-plan.md
docs/features/story-orchestrator.md
docs/testing/integration-tests.md
tests/integration/test_end_to_end_headless.py

=== DIFF ===
diff --git a/.github/notes/plans/issue-212-plan.md b/.github/notes/plans/issue-212-plan.md
new file mode 100644
index 0000000..8b739f5
--- /dev/null
+++ b/.github/notes/plans/issue-212-plan.md
@@ -0,0 +1,44 @@
+# Plan — Issue #212: Strengthen live headless E2E artifact assertions after wiki initialization
+
+## Summary
+Extend the existing live headless E2E in `tests/integration/test_end_to_end_headless.py` to assert that the completed pipeline produces wiki artifacts. Wiki initialization was already wired in PR #216 (commit b203a19). This change adds focused assertions only — no production code changes.
+
+## Affected Areas
+- Testing: `tests/integration/test_end_to_end_headless.py`
+- No production code changes
+- No ChromaDB schema changes
+
+## Task Checklist
+
+1. Add wiki directory existence assertion (`wiki/`)
+2. Add `wiki/index.md` existence assertion
+3. Add `wiki/log.md` existence + content assertion (must contain `[batch]` entries)
+4. Add `pipeline_state.json` `wiki_batches` assertion:
+   - Key exists
+   - Is a list with >= 2 entries (one per chapter)
+   - Each entry has `story_name`, `chapter_number`, `updated_pages`, `new_pages`
+   - `updated_pages` and `new_pages` are lists
+5. Add wiki subdirectory existence assertion (at least `timeline/`)
+
+## Execution Order
+Implementation → Verification tests → Confirm all pass
+
+## Risks & Edge Cases
+- Wiki pages are LLM-extracted; counts of new/updated pages may be zero. Do NOT assert non-empty `new_pages` or `updated_pages`.
+- `log.md` content depends on `run_batch` logging, which is deterministic.
+- E2E is gated behind `@pytest.mark.integration` and auto-skips if LM Studio is unavailable.
+
+## PR Description Template
+
+### Summary
+Strengthens live headless E2E assertions for wiki artifacts after wiki initialization fix.
+
+### Closes
+Closes #212
+
+### Changes
+- [x] E2E asserts wiki directory initialization
+- [x] E2E asserts wiki log and index files
+- [x] E2E asserts `wiki_batches` persisted in pipeline state
+- [x] All tests passing (verified)
+- [x] Linting clean

diff --git a/docs/features/story-orchestrator.md b/docs/features/story-orchestrator.md
index e0e1fc3..f76815e 100644
--- a/docs/features/story-orchestrator.md
+++ b/docs/features/story-orchestrator.md
@@ -19,7 +19,7 @@ The current orchestrator runs these phases in order:
 
 ```text
 Init → Outline → [Outline Gate] → Narrative Arc → Characters → Settings
-→ Chapter Loop → Final Edit → Assembly
+→ Wiki Init → Chapter Loop → Final Edit → Assembly
 ```
 
 The top-level flow lives in `run_pipeline()` and `_continue_pipeline()`.
@@ -31,6 +31,7 @@ The top-level flow lives in `run_pipeline()` and `_continue_pipeline()`.
 | `narrative-arc` | If `state.outline_result` exists, run `StoryPlannerAgent`, stream the arc assessment onto `TokenStreamBus`, store `ArcAnalysisResult` in `state.arc_result`, and continue even if the agent raises | `arc_analysis_complete` |
 | `characters` | Emit a wiki-context event, build `story_elements` from the outline, extract character names through the configured LLM, generate one sheet per extracted name, and atomically write `stories/<story>/characters/<slug>.json` | `characters` |
 | `settings` | Emit a wiki-context event, build `story_elements` from the outline, extract setting names through the configured LLM, generate one sheet per extracted name, and atomically write `stories/<story>/settings/<slug>.json` | `settings` |
+| `wiki-init` | Idempotently initialise `stories/<story>/wiki/` directory structure (subdirectories, `index.md`, `log.md`, `_schema.md`, `contradictions.md`). Skips if wiki already present. Must succeed before chapter-loop wiki maintenance runs. | — (no separate savepoint) |
 | `chapter-loop` | For each chapter number, run chapter drafting, chapter gate handling, consistency check, emit any failed consistency findings to the token bus, append the approved draft to `state.approved_chapters`, write `stories/<story>/chapters/chapter_{N}.md`, then run wiki maintenance and per-chapter savepointing | `chapter-{N}`, then `chapter-loop` |
 | `final-edit` | Unless `generation.enable_final_edit` is explicitly `false`, run `FinalEditorAgent` once per approved chapter, replace `state.approved_chapters` with the edited drafts, and write `stories/<story>/output/story_edited.md` when edited content exists | `final_edit_complete` |
 | `assembly` | Read non-empty content from `state.approved_chapters`, write `stories/<story>/output/story.md`, and fail with `StoryGenerationError` if no approved chapter content exists | `assembly`, then `complete` |
@@ -224,7 +225,7 @@ These fields round-trip through `to_dict()`, `from_dict()`, and `to_json()`. The
 
 The long-term migration PRD still describes additional phases and UI surfaces that are not yet wired in this implementation. Notably absent from the current code path:
 
-- wiki initialization and initial population
+- initial wiki population (wiki directory structure is initialised, but the full initial-populate pass that creates pages from outline and sheets is not yet wired)
 - quality-reviewer and prose-scrubber execution
 - resume-from-arbitrary-historical-savepoint behavior
 
diff --git a/docs/testing/integration-tests.md b/docs/testing/integration-tests.md
index 8f1e623..bdd936a 100644
--- a/docs/testing/integration-tests.md
+++ b/docs/testing/integration-tests.md
@@ -164,6 +164,7 @@ Across the current integration files, coverage includes these checkpoints:
 14. `savepoints/pipeline_state.json` is written during the headless run.
 15. At least two approved chapters are present with `Chapter` in the title and non-empty content.
 16. Headless runtime stays within the 600-second budget.
+17. Wiki artifacts (`wiki/index.md`, `wiki/log.md`, `wiki/timeline/`) exist after the headless run and `pipeline_state.json` contains `wiki_batches` with per-chapter `updated_pages` and `new_pages` entries.
 
 ## Manual Verification
 
diff --git a/tests/integration/test_end_to_end_headless.py b/tests/integration/test_end_to_end_headless.py
index 903f690..a6bdff0 100644
--- a/tests/integration/test_end_to_end_headless.py
+++ b/tests/integration/test_end_to_end_headless.py
@@ -128,3 +128,43 @@ def test_two_chapter_story_batch(e2e_story_dir: Path) -> None:
     assert len(chapter_files) >= 2, (
         f"Expected >= 2 chapter files, found {len(chapter_files)}"
     )
+
+    # --- Wiki assertions ---
+
+    wiki_dir = e2e_story_dir / "wiki"
+    assert wiki_dir.exists(), "wiki directory was not created"
+
+    # Wiki index exists
+    assert (wiki_dir / "index.md").exists(), "wiki/index.md was not created"
+
+    # Wiki log exists and contains batch entries from run_batch
+    log_md = wiki_dir / "log.md"
+    assert log_md.exists(), "wiki/log.md was not created"
+    log_content = log_md.read_text(encoding="utf-8")
+    assert "[batch]" in log_content, "log.md missing batch entries"
+
+    # pipeline_state.json contains wiki_batches
+    assert "wiki_batches" in state_data, "pipeline_state.json missing wiki_batches"
+    wiki_batches = state_data["wiki_batches"]
+    assert isinstance(wiki_batches, list), "wiki_batches is not a list"
+    assert len(wiki_batches) >= 2, (
+        f"Expected >= 2 wiki_batches, got {len(wiki_batches)}"
+    )
+
+    # Each wiki_batch has expected keys
+    for i, wb in enumerate(wiki_batches):
+        assert isinstance(wb, dict), f"wiki_batch[{i}] is not a dict"
+        assert "story_name" in wb, f"wiki_batch[{i}] missing 'story_name'"
+        assert "chapter_number" in wb, f"wiki_batch[{i}] missing 'chapter_number'"
+        assert "updated_pages" in wb, f"wiki_batch[{i}] missing 'updated_pages'"
+        assert "new_pages" in wb, f"wiki_batch[{i}] missing 'new_pages'"
+        assert isinstance(wb.get("updated_pages"), list), (
+            f"wiki_batch[{i}] updated_pages is not a list"
+        )
+        assert isinstance(wb.get("new_pages"), list), (
+            f"wiki_batch[{i}] new_pages is not a list"
+        )
+
+    # Wiki subdirectory exists (timeline is guaranteed because run_batch ensures dirs)
+    timeline_dir = wiki_dir / "timeline"
+    assert timeline_dir.exists(), "wiki/timeline directory was not created"

=== FILE CONTENTS ===
--- tests/integration/test_end_to_end_headless.py ---
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

    # Assert assembly wrote the output file
    story_md = e2e_story_dir / "output" / "story.md"
    assert story_md.exists(), "story.md was not produced by assembly"
    assert story_md.stat().st_size > 100, "story.md is suspiciously small (< 100 bytes)"

    # Assert individual chapter files were written
    chapter_files = list((e2e_story_dir / "chapters").glob("chapter_*.md"))
    assert len(chapter_files) >= 2, (
        f"Expected >= 2 chapter files, found {len(chapter_files)}"
    )

    # --- Wiki assertions ---

    wiki_dir = e2e_story_dir / "wiki"
    assert wiki_dir.exists(), "wiki directory was not created"

    # Wiki index exists
    assert (wiki_dir / "index.md").exists(), "wiki/index.md was not created"

    # Wiki log exists and contains batch entries from run_batch
    log_md = wiki_dir / "log.md"
    assert log_md.exists(), "wiki/log.md was not created"
    log_content = log_md.read_text(encoding="utf-8")
    assert "[batch]" in log_content, "log.md missing batch entries"

    # pipeline_state.json contains wiki_batches
    assert "wiki_batches" in state_data, "pipeline_state.json missing wiki_batches"
    wiki_batches = state_data["wiki_batches"]
    assert isinstance(wiki_batches, list), "wiki_batches is not a list"
    assert len(wiki_batches) >= 2, (
        f"Expected >= 2 wiki_batches, got {len(wiki_batches)}"
    )

    # Each wiki_batch has expected keys
    for i, wb in enumerate(wiki_batches):
        assert isinstance(wb, dict), f"wiki_batch[{i}] is not a dict"
        assert "story_name" in wb, f"wiki_batch[{i}] missing 'story_name'"
        assert "chapter_number" in wb, f"wiki_batch[{i}] missing 'chapter_number'"
        assert "updated_pages" in wb, f"wiki_batch[{i}] missing 'updated_pages'"
        assert "new_pages" in wb, f"wiki_batch[{i}] missing 'new_pages'"
        assert isinstance(wb.get("updated_pages"), list), (
            f"wiki_batch[{i}] updated_pages is not a list"
        )
        assert isinstance(wb.get("new_pages"), list), (
            f"wiki_batch[{i}] new_pages is not a list"
        )

    # Wiki subdirectory exists (timeline is guaranteed because run_batch ensures dirs)
    timeline_dir = wiki_dir / "timeline"
    assert timeline_dir.exists(), "wiki/timeline directory was not created"

--- docs/features/story-orchestrator.md ---
# Story Orchestrator

> Headless Python pipeline runner and agent-callable layer implemented in Issue #161 / PR #171, extended with characters and settings in Issue #182 / PR #194, consistency-result parsing in Issue #184 / PR #197, and narrative-arc plus final-edit execution in Issue #185 / PR #198.

## Overview

Issue #161 implements the first executable Python-native orchestration slice in `src/presentation/orchestrator.py`. Issue #182 extends that slice by replacing the characters and settings stubs with real sheet-generation helpers and by teaching the chapter writer to consume those generated sheets as prompt context. Issue #185 adds the missing Phase 2.5 narrative-arc pass and replaces the Phase 9 final-edit stub with a real editing agent. The current implementation still remains smaller than the long-term PRD: it runs a headless async pipeline, persists one JSON savepoint file, and coordinates Python presentation agents plus orchestrator-local helper phases through injected transport primitives.

Two entry points exist:

- `run_pipeline(story_name, gate, bus, wiki_bus)` starts a new run, writes the initial `init` savepoint, then advances through the implemented phases.
- `resume_pipeline(story_name, savepoint_name, gate, bus, wiki_bus)` reloads persisted `PipelineState` from `stories/<story>/savepoints/pipeline_state.json` and continues from the stored phase state.

This slice does not yet implement the full PRD phase map. The current code path is the authoritative behavior for documentation and testing.

## Implemented Phase Sequence

The current orchestrator runs these phases in order:

```text
Init → Outline → [Outline Gate] → Narrative Arc → Characters → Settings
→ Wiki Init → Chapter Loop → Final Edit → Assembly
```

The top-level flow lives in `run_pipeline()` and `_continue_pipeline()`.

| Phase | Controller behavior | Savepoint written |
|------|----------------------|-------------------|
| `init` | Create initial `PipelineState`, detect batch mode from gate type, ensure `stories/<story>/savepoints/` exists | `init` |
| `outline` | Run `OutlinePlannerAgent`, persist `OutlineResult`, then wait on the outline approval gate | `outline` |
| `narrative-arc` | If `state.outline_result` exists, run `StoryPlannerAgent`, stream the arc assessment onto `TokenStreamBus`, store `ArcAnalysisResult` in `state.arc_result`, and continue even if the agent raises | `arc_analysis_complete` |
| `characters` | Emit a wiki-context event, build `story_elements` from the outline, extract character names through the configured LLM, generate one sheet per extracted name, and atomically write `stories/<story>/characters/<slug>.json` | `characters` |
| `settings` | Emit a wiki-context event, build `story_elements` from the outline, extract setting names through the configured LLM, generate one sheet per extracted name, and atomically write `stories/<story>/settings/<slug>.json` | `settings` |
| `wiki-init` | Idempotently initialise `stories/<story>/wiki/` directory structure (subdirectories, `index.md`, `log.md`, `_schema.md`, `contradictions.md`). Skips if wiki already present. Must succeed before chapter-loop wiki maintenance runs. | — (no separate savepoint) |
| `chapter-loop` | For each chapter number, run chapter drafting, chapter gate handling, consistency check, emit any failed consistency findings to the token bus, append the approved draft to `state.approved_chapters`, write `stories/<story>/chapters/chapter_{N}.md`, then run wiki maintenance and per-chapter savepointing | `chapter-{N}`, then `chapter-loop` |
| `final-edit` | Unless `generation.enable_final_edit` is explicitly `false`, run `FinalEditorAgent` once per approved chapter, replace `state.approved_chapters` with the edited drafts, and write `stories/<story>/output/story_edited.md` when edited content exists | `final_edit_complete` |
| `assembly` | Read non-empty content from `state.approved_chapters`, write `stories/<story>/output/story.md`, and fail with `StoryGenerationError` if no approved chapter content exists | `assembly`, then `complete` |

Chapter count comes from `OutlineResult.chapter_outlines` when present. If the outline did not produce chapter entries, the fallback is `range(1, min(settings.wanted_chapters, 3) + 1)`.

The characters and settings phases are implemented as orchestrator helpers rather than standalone presentation agents. `_build_story_elements()` derives the prompt input directly from `OutlineResult`, so these phases do not depend on a separate outline savepoint artefact.

## Runtime Outputs

The current orchestrator writes five story-facing artifact groups during a successful run:

- `stories/<story>/savepoints/pipeline_state.json` — the persisted `PipelineState` snapshot, including `arc_result` when narrative-arc succeeds
- `stories/<story>/characters/<slug>.json` — one JSON character sheet per extracted name
- `stories/<story>/settings/<slug>.json` — one JSON setting sheet per extracted name
- `stories/<story>/chapters/chapter_{N}.md` — written immediately after chapter `N` passes the approval gate and consistency check

--- docs/testing/integration-tests.md ---
(Partial content — lines 150-180)
Across the current integration files, coverage includes these checkpoints:

14. `savepoints/pipeline_state.json` is written during the headless run.
15. At least two approved chapters are present with `Chapter` in the title and non-empty content.
16. Headless runtime stays within the 600-second budget.
17. Wiki artifacts (`wiki/index.md`, `wiki/log.md`, `wiki/timeline/`) exist after the headless run and `pipeline_state.json` contains `wiki_batches` with per-chapter `updated_pages` and `new_pages` entries.

## Manual Verification

After a successful run, inspect the temporary story path printed at the start of the test session (`Integration story dir: ...`). Review these outputs manually when you need extra confidence beyond pytest assertions:

- `stories/<temp>/e2e-test-story/wiki/index.md` — wiki page inventory
- `stories/<temp>/e2e-test-story/wiki/log.md` — wiki operation log
- `stories/<temp>/e2e-test-story/wiki/characters/*.md` — generated character pages
- `stories/<temp>/e2e-test-story/wiki/locations/*.md` — generated location pages
- `stories/<temp>/e2e-test-story/wiki/chapters/*.md` — generated chapter pages
- `stories/<temp>/e2e-test-story/chapters/chapter_*.md` — approved chapter files written during the per-chapter loop
- `stories/<temp>/e2e-test-story/output/story.md` — final manuscript assembled from approved chapters
- `stories/<temp>/e2e-test-story/savepoints/` — intermediate savepoints across the pipeline

== END REVIEW PACKAGE ==
