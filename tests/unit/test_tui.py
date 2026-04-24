"""Tests for the Textual TUI - issue #163."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from application.pipeline.handoffs import ApprovalDecision
from presentation.tui.app import StoryWriterApp


class TestStoryWriterAppInit:
    @pytest.mark.asyncio
    async def test_app_composes_without_error(self) -> None:
        """StoryWriterApp initialises and renders without exceptions."""
        with patch("presentation.tui.app.StoryWriterApp._run_pipeline"):
            app = StoryWriterApp(story_name="test_story")
            async with app.run_test(size=(120, 40)):
                assert app.story_name == "test_story"

    @pytest.mark.asyncio
    async def test_approval_input_hidden_on_mount(self) -> None:
        """Approval input widget is hidden initially."""
        with patch("presentation.tui.app.StoryWriterApp._run_pipeline"):
            app = StoryWriterApp(story_name="test_story")
            async with app.run_test(size=(120, 40)):
                input_widget = app.query_one("#approval-input")
                assert input_widget.display is False

    @pytest.mark.asyncio
    async def test_wiki_panel_hidden_on_mount(self) -> None:
        """Wiki context panel is hidden initially."""
        with patch("presentation.tui.app.StoryWriterApp._run_pipeline"):
            app = StoryWriterApp(story_name="test_story")
            async with app.run_test(size=(120, 40)):
                wiki_panel = app.query_one("#wiki-panel")
                assert wiki_panel.display is False

    @pytest.mark.asyncio
    async def test_output_log_disables_markup(self) -> None:
        """Output log treats LLM token text as literal text."""
        with patch("presentation.tui.app.StoryWriterApp._run_pipeline"):
            app = StoryWriterApp(story_name="test_story")
            async with app.run_test(size=(120, 40)):
                output_log = app.query_one("#output-log")
                assert output_log.markup is False


class TestWikiPanelToggle:
    @pytest.mark.asyncio
    async def test_ctrl_w_shows_wiki_panel(self) -> None:
        """Ctrl+W makes the wiki panel visible."""
        with patch("presentation.tui.app.StoryWriterApp._run_pipeline"):
            app = StoryWriterApp(story_name="test_story")
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.press("ctrl+w")
                assert app.query_one("#wiki-panel").display is True

    @pytest.mark.asyncio
    async def test_ctrl_w_toggles_wiki_panel_off(self) -> None:
        """Second Ctrl+W hides the wiki panel."""
        with patch("presentation.tui.app.StoryWriterApp._run_pipeline"):
            app = StoryWriterApp(story_name="test_story")
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.press("ctrl+w")
                await pilot.press("ctrl+w")
                assert app.query_one("#wiki-panel").display is False


class TestApprovalGate:
    def test_parse_approval_input_approve(self) -> None:
        from presentation.tui.app import _parse_approval_input

        result = _parse_approval_input("approve")
        assert result.approved is True

    def test_parse_approval_input_reject(self) -> None:
        from presentation.tui.app import _parse_approval_input

        result = _parse_approval_input("reject")
        assert result.approved is False
        assert result.feedback is None

    def test_parse_approval_input_revise(self) -> None:
        from presentation.tui.app import _parse_approval_input

        result = _parse_approval_input("revise needs more action")
        assert result.approved is False
        assert result.feedback == "needs more action"

    def test_parse_approval_input_free_text(self) -> None:
        from presentation.tui.app import _parse_approval_input

        result = _parse_approval_input("make it longer")
        assert result.approved is False
        assert result.feedback == "make it longer"

    @pytest.mark.asyncio
    async def test_approval_input_submit_resolves_gate(self) -> None:
        """Submitting the approval input resolves the TUI gate."""
        from presentation.tui.app import TUIApprovalGate

        with patch("presentation.tui.app.StoryWriterApp._run_pipeline"):
            app = StoryWriterApp(story_name="test_story")
            async with app.run_test(size=(120, 40)) as pilot:
                gate = TUIApprovalGate(app)
                app._gate = gate
                app._show_approval_input()
                await pilot.pause(0.1)

                loop = asyncio.get_running_loop()
                future: asyncio.Future[ApprovalDecision] = loop.create_future()
                gate._worker_loop = loop
                gate._future = future

                input_widget = app.query_one("#approval-input")
                input_widget.focus()
                await pilot.press(*"approve", "enter")
                await pilot.pause(0.1)

                assert future.done()
                assert future.result().approved is True

    @pytest.mark.asyncio
    async def test_approval_prompt_uses_plain_text(self) -> None:
        """Approval prompt should not rely on Rich markup."""
        with patch("presentation.tui.app.StoryWriterApp._run_pipeline"):
            app = StoryWriterApp(story_name="test_story")
            async with app.run_test(size=(120, 40)):
                output_log = app.query_one("#output-log")

                app._show_approval_input()

                rendered = output_log.lines[-2].text
                assert (
                    "Approval required. Type: approve / reject / revise <feedback>"
                    in rendered
                )


class TestPipelineCompletion:
    @pytest.mark.asyncio
    async def test_error_completion_does_not_mark_all_phases_complete(self) -> None:
        """Error completion should preserve current phase state and failure subtitle."""
        with patch("presentation.tui.app.StoryWriterApp._run_pipeline"):
            app = StoryWriterApp(story_name="test_story")
            async with app.run_test(size=(120, 40)):
                app._update_phase("wiki")
                app._on_pipeline_complete("error")

                assert app.sub_title == "Failed - error"
                assert app.query_one("#phase-assembly").renderable == "- assembly"


class TestQuitAction:
    @pytest.mark.asyncio
    async def test_request_quit_logs_cancellation_notice(self) -> None:
        """Quit action should tell the user cancellation is cooperative."""
        with patch("presentation.tui.app.StoryWriterApp._run_pipeline"):
            app = StoryWriterApp(story_name="test_story")
            async with app.run_test(size=(120, 40)):
                output_log = app.query_one("#output-log")

                app.action_request_quit()

                assert (
                    "Cancellation requested. Finishing current LLM call before exit..."
                    in output_log.lines[-2].text
                )


class TestTUIApprovalGate:
    def test_tui_approval_gate_resolve_from_ui(self) -> None:
        """resolve_from_ui uses call_soon_threadsafe to resolve the future."""
        from presentation.tui.app import TUIApprovalGate

        mock_app = MagicMock()
        gate = TUIApprovalGate(mock_app)

        mock_loop = MagicMock()
        mock_future = MagicMock()
        mock_future.done.return_value = False
        gate._worker_loop = mock_loop
        gate._future = mock_future

        decision = ApprovalDecision(approved=True)
        gate.resolve_from_ui(decision)

        mock_loop.call_soon_threadsafe.assert_called_once_with(
            mock_future.set_result, decision
        )
