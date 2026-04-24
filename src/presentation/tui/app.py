"""Textual TUI for the story-writer pipeline.

Three-panel layout:
- Left:   Phase tracker
- Center: RichLog streaming output
- Right:  Wiki context panel (hidden by default, toggled with Ctrl+W)

Footer: Input widget revealed only when an approval gate is active.

@work(thread=True) worker runs the async orchestrator in a background
thread. call_from_thread() bridges UI updates from the worker.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.widgets import Footer, Header, Input, Label, RichLog

_project_root = Path(__file__).resolve().parents[3]
_src_dir = _project_root / "src"

if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from application.pipeline.handoffs import ApprovalDecision, PipelineState  # noqa: E402
from presentation.orchestrator import run_pipeline  # noqa: E402
from presentation.pipeline_primitives import (  # noqa: E402
    ApprovalGate,
    TokenStreamBus,
    WikiContextBus,
    WikiContextEvent,
)

PIPELINE_PHASES = ["outline", "chapters", "wiki", "final-edit", "assembly"]


def _parse_approval_input(raw: str) -> ApprovalDecision:
    """Parse user input from the approval gate widget."""
    lower = raw.lower()
    if lower in ("approve", "y", "yes"):
        return ApprovalDecision(approved=True)
    if lower in ("reject", "n", "no"):
        return ApprovalDecision(approved=False)
    if lower.startswith("revise "):
        return ApprovalDecision(approved=False, feedback=raw[7:].strip())
    return ApprovalDecision(approved=False, feedback=raw)


class TUIApprovalGate(ApprovalGate):
    """Approval gate that bridges worker-thread asyncio to Textual UI."""

    def __init__(self, app: StoryWriterApp) -> None:
        super().__init__()
        self._app = app
        self._worker_loop: asyncio.AbstractEventLoop | None = None

    async def await_decision(self) -> ApprovalDecision:
        if self._pending_decision is not None:
            result = self._pending_decision
            self._pending_decision = None
            return result

        loop = asyncio.get_running_loop()
        self._worker_loop = loop
        self._future = loop.create_future()
        self._app.call_from_thread(self._app._show_approval_input)
        return await self._future

    def resolve_from_ui(self, decision: ApprovalDecision) -> None:
        """Called from the Textual event loop to resolve the gate."""
        if self._worker_loop and self._future and not self._future.done():
            self._worker_loop.call_soon_threadsafe(self._future.set_result, decision)
            return
        self._pending_decision = decision


class StoryWriterApp(App[None]):
    """Textual app for streaming story pipeline progress."""

    CSS_PATH = "app.tcss"

    BINDINGS = [
        Binding("ctrl+w", "toggle_wiki", "Toggle wiki panel"),
        Binding("ctrl+s", "force_savepoint", "Save checkpoint"),
        Binding("ctrl+c", "request_quit", "Quit", show=True),
    ]

    def __init__(self, story_name: str) -> None:
        super().__init__()
        self.story_name = story_name
        self._gate: TUIApprovalGate | None = None
        self._wiki_visible = False
        self._completed_phases: list[str] = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main-grid"):
            with Vertical(id="phase-panel"):
                yield Label("Phases", id="phase-title")
                for phase in PIPELINE_PHASES:
                    yield Label(f"- {phase}", id=f"phase-{phase}", classes="phase-item")
            yield RichLog(id="output-log", highlight=True, markup=True, wrap=True)
            with Vertical(id="wiki-panel"):
                yield Label("Wiki Context", id="wiki-title")
                yield RichLog(id="wiki-log", highlight=False, markup=False, wrap=True)
        yield Input(
            placeholder="approve / reject / revise <feedback>",
            id="approval-input",
        )
        yield Footer()

    def on_mount(self) -> None:
        self.title = f"Story Writer - {self.story_name}"
        self.sub_title = "Initializing..."
        self.query_one("#approval-input", Input).display = False
        self.query_one("#wiki-panel", Vertical).display = False
        self._update_phase("outline")
        self._run_pipeline(self.story_name)

    def _append_token(self, delta: str) -> None:
        """Append a token delta to the output log."""
        self.query_one("#output-log", RichLog).write(delta)

    def _append_wiki_event(self, event: WikiContextEvent) -> None:
        """Append a wiki context event to the wiki panel."""
        self._update_phase(self._normalize_phase(event.phase))
        self.query_one("#wiki-log", RichLog).write(
            f"[{event.phase}] {event.event_type}: {event.content}"
        )

    def _append_error(self, message: str) -> None:
        """Append a pipeline error to the output log."""
        self.query_one("#output-log", RichLog).write(
            f"\n[bold red]Pipeline error: {message}[/bold red]\n"
        )

    def _normalize_phase(self, phase: str) -> str:
        """Map internal pipeline phase names onto the simplified TUI phases."""
        if phase.startswith("chapter-") or phase == "chapter-loop":
            return "chapters"
        if phase in {"characters", "settings", "wiki"}:
            return "wiki"
        if phase in PIPELINE_PHASES:
            return phase
        return "outline"

    def _update_phase(self, phase: str) -> None:
        """Update phase indicators."""
        normalized = self._normalize_phase(phase)
        self.sub_title = f"Phase: {normalized}"

        current_index = PIPELINE_PHASES.index(normalized)
        self._completed_phases = PIPELINE_PHASES[:current_index]

        for index, pipeline_phase in enumerate(PIPELINE_PHASES):
            label = self.query_one(f"#phase-{pipeline_phase}", Label)
            if index < current_index:
                label.update(f"* {pipeline_phase}")
            elif pipeline_phase == normalized:
                label.update(f"> {pipeline_phase}")
            else:
                label.update(f"- {pipeline_phase}")

    def _show_approval_input(self) -> None:
        """Reveal the approval input widget."""
        input_widget = self.query_one("#approval-input", Input)
        input_widget.display = True
        input_widget.focus()
        self.query_one("#output-log", RichLog).write(
            "\n[bold yellow]Approval required. Type: approve / reject / revise <feedback>[/bold yellow]\n"
        )

    def _hide_approval_input(self) -> None:
        """Hide the approval input widget after submission."""
        input_widget = self.query_one("#approval-input", Input)
        input_widget.display = False
        input_widget.clear()

    def _on_pipeline_complete(self, status: str) -> None:
        """Update the UI when the pipeline finishes."""
        self._completed_phases = PIPELINE_PHASES[:]
        for phase in PIPELINE_PHASES:
            self.query_one(f"#phase-{phase}", Label).update(f"* {phase}")
        self.sub_title = f"Complete - {status}"
        self.query_one("#output-log", RichLog).write(
            f"\n[bold green]Pipeline complete: {status}[/bold green]\n"
        )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle approval gate submission."""
        if event.input.id != "approval-input":
            return

        raw = event.value.strip()
        if not raw:
            return

        decision = _parse_approval_input(raw)
        self._hide_approval_input()
        if self._gate is not None:
            self._gate.resolve_from_ui(decision)

    def action_toggle_wiki(self) -> None:
        """Toggle the wiki context panel."""
        self._wiki_visible = not self._wiki_visible
        self.query_one("#wiki-panel", Vertical).display = self._wiki_visible

    def action_force_savepoint(self) -> None:
        """Show informational savepoint message."""
        self.query_one("#output-log", RichLog).write(
            "\n[bold cyan]Savepoint requested (automatic savepoints are written at each phase boundary)[/bold cyan]\n"
        )

    def action_request_quit(self) -> None:
        """Cancel workers and exit."""
        for worker in self.workers:
            worker.cancel()
        self.exit()

    @work(thread=True)
    def _run_pipeline(self, story_name: str) -> None:
        """Background worker: runs the async pipeline and bridges events to UI."""
        gate = TUIApprovalGate(self)
        self._gate = gate

        async def _drain_tokens(bus: TokenStreamBus) -> None:
            async for delta in bus:
                self.call_from_thread(self._append_token, delta)

        async def _drain_wiki(wiki_bus: WikiContextBus) -> None:
            async for event in wiki_bus:
                self.call_from_thread(self._append_wiki_event, event)

        async def _pipeline_with_close(
            bus: TokenStreamBus, wiki_bus: WikiContextBus
        ) -> PipelineState:
            try:
                return await run_pipeline(story_name, gate, bus, wiki_bus)
            finally:
                bus.close()
                wiki_bus.close()

        async def _run() -> None:
            bus = TokenStreamBus()
            wiki_bus = WikiContextBus()
            try:
                state, _, _ = await asyncio.gather(
                    _pipeline_with_close(bus, wiki_bus),
                    _drain_tokens(bus),
                    _drain_wiki(wiki_bus),
                )
                self.call_from_thread(self._on_pipeline_complete, state.status)
            except Exception as exc:
                self.call_from_thread(self._append_error, str(exc))
                self.call_from_thread(self._on_pipeline_complete, "error")

        asyncio.run(_run())
