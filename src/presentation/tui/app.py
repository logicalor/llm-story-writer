"""Textual TUI for the story-writer pipeline.

Layout:
- Left:   Phase tracker (dynamic, fed by StatusBus events)
- Center: RichLog streaming output (LLM tokens + step banners)
- Right:  Wiki context panel (hidden by default, toggled with Ctrl+W)
- Bottom (above footer): Activity bar - current phase, elapsed time,
                         token count and rate, last status message.
- Footer: Approval input revealed only at approval gates.

@work(thread=True) worker runs the async orchestrator in a background
thread. call_from_thread() bridges UI updates from the worker.
"""

from __future__ import annotations

import asyncio
import sys
import time
from datetime import datetime
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
from presentation.orchestrator import resume_pipeline, run_pipeline  # noqa: E402
from presentation.pipeline_primitives import (  # noqa: E402
    ApprovalGate,
    StatusBus,
    StatusEvent,
    TokenStreamBus,
    WikiContextBus,
    WikiContextEvent,
)

# Ordered list of phases the orchestrator may walk through. The phase tracker
# panel renders this list; phases that are encountered dynamically (chapter-N)
# get inserted in order as StatusEvents arrive.
KNOWN_PHASES: list[str] = [
    "story-foundation",
    "outline",
    "outline-critique",
    "metadata-outline",
    "narrative-arc",
    "characters",
    "settings",
    "wiki-bootstrap",
    "chapter-loop",
    "final-edit",
    "metadata-final",
    "assembly",
    "complete",
]


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
        Binding("ctrl+w", "toggle_wiki", "Toggle wiki panel", priority=True),
        Binding("ctrl+c", "request_quit", "Cancel", show=True),
    ]

    def __init__(
        self,
        story_name: str,
        resume: bool = False,
        savepoint_name: str | None = None,
    ) -> None:
        super().__init__()
        self.story_name = story_name
        self.resume = resume
        self.savepoint_name = savepoint_name
        self._gate: TUIApprovalGate | None = None
        self._wiki_visible = True
        self._token_buffer: list[str] = []

        # Visibility tracking
        self._phase_order: list[str] = list(KNOWN_PHASES)
        self._completed_phases: set[str] = set()
        self._current_phase: str | None = None
        self._phase_started_at: float | None = None
        self._last_status_message: str = "Initializing..."
        self._token_count: int = 0
        self._token_window: list[tuple[float, int]] = []  # (timestamp, total)
        self._last_activity_at: float = time.monotonic()

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main-grid"):
            with Vertical(id="phase-panel"):
                yield Label("Phases", id="phase-title")
                with Vertical(id="phase-list"):
                    for phase in self._phase_order:
                        yield Label(
                            f"  {phase}",
                            id=f"phase-{phase}",
                            classes="phase-item phase-pending",
                        )
            yield RichLog(id="output-log", highlight=False, markup=False, wrap=True)
            with Vertical(id="wiki-panel"):
                yield Label("Activity", id="wiki-title")
                yield RichLog(id="wiki-log", highlight=False, markup=False, wrap=True)
        yield Label("idle", id="status-bar")
        yield Input(
            placeholder="approve / reject / revise <feedback>",
            id="approval-input",
        )
        yield Footer()

    def on_mount(self) -> None:
        self.title = f"Story Writer - {self.story_name}"
        self.sub_title = "Initializing..."
        self.query_one("#approval-input", Input).display = False
        self.query_one("#wiki-panel", Vertical).display = self._wiki_visible
        # Refresh the activity bar every second so elapsed times tick.
        self.set_interval(1.0, self._refresh_status_bar)
        self._run_pipeline(self.story_name, self.resume, self.savepoint_name)

    # ------------------------------------------------------------------ tokens

    def _flush_token_buffer(self) -> None:
        if not self._token_buffer:
            return
        text = "".join(self._token_buffer)
        self._token_buffer.clear()
        self.query_one("#output-log", RichLog).write(text)

    def _append_token(self, delta: str) -> None:
        self._token_buffer.append(delta)
        self._token_count += len(delta)
        now = time.monotonic()
        self._last_activity_at = now
        # Track token totals on a rolling 5s window for rate calculation.
        self._token_window.append((now, self._token_count))
        cutoff = now - 5.0
        while len(self._token_window) > 1 and self._token_window[0][0] < cutoff:
            self._token_window.pop(0)
        if "\n" in delta or len(self._token_buffer) > 120:
            self._flush_token_buffer()

    # -------------------------------------------------------------- wiki panel

    # Map internal event_type values to short human-readable prefixes.
    _EVENT_SYMBOLS: dict[str, str] = {
        "entity_match": "●",
        "wikilink_traversal": "→",
        "detail_level": "›",
    }

    def _append_wiki_event(self, event: WikiContextEvent) -> None:
        symbol = self._EVENT_SYMBOLS.get(event.event_type, "·")
        ts = datetime.now().strftime("%H:%M:%S")
        self.query_one("#wiki-log", RichLog).write(
            f"{ts} {symbol} [{event.phase}] {event.content}"
        )
        self._last_activity_at = time.monotonic()

    # ------------------------------------------------------------------- error

    def _append_error(self, message: str) -> None:
        self._flush_token_buffer()
        self.query_one("#output-log", RichLog).write(f"\nPipeline error: {message}\n")

    # ------------------------------------------------------------ status events

    def _ensure_phase_in_tracker(self, phase: str) -> None:
        if phase in self._phase_order:
            return
        # Insert dynamic phases (e.g. chapter-3) before the first phase that
        # comes after them in the canonical lifecycle. Chapter phases live
        # between wiki-bootstrap and final-edit.
        anchor_id: str
        if phase.startswith("chapter-"):
            try:
                anchor_index = self._phase_order.index("final-edit")
            except ValueError:
                anchor_index = len(self._phase_order)
            self._phase_order.insert(anchor_index, phase)
            anchor_id = "phase-final-edit"
        else:
            self._phase_order.append(phase)
            anchor_id = ""

        new_label = Label(
            f"  {phase}",
            id=f"phase-{phase}",
            classes="phase-item phase-pending",
        )
        phase_list = self.query_one("#phase-list", Vertical)
        if anchor_id:
            try:
                anchor_widget = self.query_one(f"#{anchor_id}", Label)
                phase_list.mount(new_label, before=anchor_widget)
                return
            except Exception:
                pass
        phase_list.mount(new_label)

    def _set_phase_label(self, phase: str, marker: str, css_class: str) -> None:
        try:
            label = self.query_one(f"#phase-{phase}", Label)
        except Exception:
            return
        label.update(f"{marker} {phase}")
        label.set_classes(f"phase-item {css_class}")

    def _handle_status_event(self, event: StatusEvent) -> None:
        self._ensure_phase_in_tracker(event.phase)
        self._last_status_message = event.message
        self._last_activity_at = time.monotonic()

        if event.kind == "phase_start":
            # Mark previous current as completed if different
            if (
                self._current_phase
                and self._current_phase != event.phase
                and self._current_phase not in self._completed_phases
            ):
                self._completed_phases.add(self._current_phase)
                self._set_phase_label(self._current_phase, "*", "phase-done")
            self._current_phase = event.phase
            self._phase_started_at = time.monotonic()
            self._set_phase_label(event.phase, ">", "phase-active")
            self._flush_token_buffer()
            self.query_one("#output-log", RichLog).write(
                f"\n>>> {event.phase}: {event.message}\n"
            )
        elif event.kind == "phase_end":
            self._completed_phases.add(event.phase)
            self._set_phase_label(event.phase, "*", "phase-done")
            if self._current_phase == event.phase:
                self._current_phase = None
                self._phase_started_at = None
        elif event.kind == "awaiting":
            self._set_phase_label(event.phase, "?", "phase-awaiting")
        elif event.kind == "error":
            self._set_phase_label(event.phase, "!", "phase-error")

        # Log step/info/warn/error events into the Activity panel as well, so
        # users have a scrollable history of substep progress (per-character,
        # per-scene, etc.) rather than only the latest line in the status bar.
        if event.kind in ("step", "info", "warn", "error"):
            symbol = {
                "step": "›",
                "info": "·",
                "warn": "!",
                "error": "✗",
            }.get(event.kind, "·")
            ts = datetime.now().strftime("%H:%M:%S")
            try:
                self.query_one("#wiki-log", RichLog).write(
                    f"{ts} {symbol} [{event.phase}] {event.message}"
                )
            except Exception:
                pass

        self._refresh_status_bar()

    # ------------------------------------------------------------- status bar

    def _refresh_status_bar(self) -> None:
        now = time.monotonic()

        # Elapsed in current phase
        if self._phase_started_at is not None:
            elapsed = int(now - self._phase_started_at)
            elapsed_str = f"{elapsed // 60}m{elapsed % 60:02d}s"
        else:
            elapsed_str = "--"

        # Token rate over rolling window
        if len(self._token_window) >= 2:
            t0, n0 = self._token_window[0]
            t1, n1 = self._token_window[-1]
            dt = max(t1 - t0, 1e-6)
            rate = (n1 - n0) / dt
        else:
            rate = 0.0

        # Idle indicator
        idle = int(now - self._last_activity_at)
        idle_str = f" idle {idle}s" if idle > 3 else ""

        phase_str = self._current_phase or "(none)"

        bar = (
            f"phase: {phase_str}  elapsed: {elapsed_str}  "
            f"chars: {self._token_count}  rate: {rate:5.1f}/s{idle_str}  "
            f"| {self._last_status_message}"
        )
        try:
            self.query_one("#status-bar", Label).update(bar)
        except Exception:
            pass
        self.sub_title = f"{phase_str} ({elapsed_str})"

    # ------------------------------------------------------------- approvals

    def _show_approval_input(self) -> None:
        self._flush_token_buffer()
        input_widget = self.query_one("#approval-input", Input)
        input_widget.display = True
        input_widget.focus()
        self.query_one("#output-log", RichLog).write(
            "\nApproval required. Type: approve / reject / revise <feedback>\n"
        )

    def _hide_approval_input(self) -> None:
        input_widget = self.query_one("#approval-input", Input)
        input_widget.display = False
        input_widget.clear()

    def _on_pipeline_complete(self, status: str) -> None:
        self._flush_token_buffer()
        if status == "error":
            self.sub_title = f"Failed - {status}"
            self.query_one("#output-log", RichLog).write(
                f"\nPipeline failed: {status}\n"
            )
            return

        for phase in self._phase_order:
            if phase != "complete":
                self._set_phase_label(phase, "*", "phase-done")
        self._set_phase_label("complete", "*", "phase-done")
        self.sub_title = f"Complete - {status}"
        self.query_one("#output-log", RichLog).write(f"\nPipeline complete: {status}\n")

    def on_input_submitted(self, event: Input.Submitted) -> None:
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
        self._wiki_visible = not self._wiki_visible
        self.query_one("#wiki-panel", Vertical).display = self._wiki_visible

    def action_request_quit(self) -> None:
        # Cancel workers and let Textual restore the terminal (cooked mode,
        # alt-screen leave). main.py force-exits the process after app.run()
        # returns, killing the pipeline worker thread.
        for worker in self.workers:
            worker.cancel()
        self.exit()

    @work(thread=True)
    def _run_pipeline(
        self,
        story_name: str,
        resume: bool = False,
        savepoint_name: str | None = None,
    ) -> None:
        """Background worker: runs the async pipeline and bridges events to UI."""
        gate = TUIApprovalGate(self)
        self._gate = gate

        async def _drain_tokens(bus: TokenStreamBus) -> None:
            async for delta in bus:
                self.call_from_thread(self._append_token, delta)

        async def _drain_wiki(wiki_bus: WikiContextBus) -> None:
            async for event in wiki_bus:
                self.call_from_thread(self._append_wiki_event, event)

        async def _drain_status(status_bus: StatusBus) -> None:
            async for event in status_bus:
                self.call_from_thread(self._handle_status_event, event)

        async def _pipeline_with_close(
            bus: TokenStreamBus,
            wiki_bus: WikiContextBus,
            status_bus: StatusBus,
        ) -> PipelineState:
            try:
                if resume:
                    return await resume_pipeline(
                        story_name,
                        savepoint_name,
                        gate,
                        bus,
                        wiki_bus,
                        status_bus=status_bus,
                    )
                return await run_pipeline(
                    story_name,
                    gate,
                    bus,
                    wiki_bus,
                    status_bus=status_bus,
                )
            finally:
                bus.close()
                wiki_bus.close()
                status_bus.close()

        async def _run() -> None:
            bus = TokenStreamBus()
            wiki_bus = WikiContextBus()
            status_bus = StatusBus()
            try:
                state, _, _, _ = await asyncio.gather(
                    _pipeline_with_close(bus, wiki_bus, status_bus),
                    _drain_tokens(bus),
                    _drain_wiki(wiki_bus),
                    _drain_status(status_bus),
                )
                self.call_from_thread(self._on_pipeline_complete, state.status)
            except Exception as exc:
                self.call_from_thread(self._append_error, str(exc))
                self.call_from_thread(self._on_pipeline_complete, "error")

        asyncio.run(_run())
