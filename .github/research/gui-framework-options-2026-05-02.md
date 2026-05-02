# Research Report: GUI Framework Options for `llm-story-writer`

**Date:** 2026-05-02
**Brief:** Identify and evaluate viable GUI frameworks to add a graphical front-end to `llm-story-writer`, alongside the existing Textual TUI (`src/presentation/tui/app.py`). The GUI must support live token streaming, multi-panel layout (phase tracker, output log, wiki context), human-in-the-loop approval gates, and run-resume flows — without rewriting the async pipeline orchestrator.
**Sources:** Tavily web search (advanced depth, 2025–2026 articles), Context7 NiceGUI documentation, project source review (`src/presentation/pipeline_primitives.py`, `docs/features/textual-tui.md`).

---

## Summary

For this project, **NiceGUI is the strongest fit**, with **PySide6 (with `qasync`/QtAsyncio) the strongest desktop-native alternative**, and **Chainlit a viable shortcut if the UX collapses to a chat-style transcript**. The current `ApprovalGate` / `TokenStreamBus` / `WikiContextBus` primitives are already transport-agnostic asyncio-based abstractions, so any framework that runs natively on `asyncio` (NiceGUI, Chainlit, Reflex, Flet) can consume them with no orchestrator changes. Frameworks built on a non-asyncio reactor (PySide6, Tk, wxPython) can still integrate but require an asyncio bridge thread — the same pattern used today by the Textual TUI.

---

## Project Constraints (Established From Codebase)

The pipeline already exposes the surface a GUI needs:

- `ApprovalGate.await_decision()` / `.resolve()` — async approval checkpoints.
- `TokenStreamBus` — single-consumer async iterator yielding token deltas.
- `WikiContextBus` — async iterator yielding structured `WikiContextEvent` objects.
- `run_pipeline()` / `resume_pipeline()` — coroutines that accept gate + buses.

Therefore the GUI layer is a **presentation-only** consumer, exactly mirroring what `StoryWriterApp` does today. The deciding factors are:

1. **Native asyncio compatibility** — to consume the buses without thread-bridging gymnastics.
2. **Streaming text rendering** — append-only log/markdown widget that updates on each token without re-rendering the whole page.
3. **Multi-panel layout** — three-pane layout (phases / log / wiki) plus a hidden approval input.
4. **Local-first deployment** — single-user desktop app, no auth/multi-tenant requirements.
5. **Cross-platform** — Linux (primary), macOS, Windows.
6. **Dependency surface** — minimal additional install burden.
7. **License** — permissive (MIT/Apache/BSD/LGPL acceptable; avoid GPL contagion via PyQt6).

---

## Findings

### Tier 1 — Recommended

#### NiceGUI (`/zauberzeug/nicegui`)

- **Type:** Browser-rendered, Python-only. FastAPI + Vue/Quasar under the hood; runs locally as `http://localhost:<port>` and can launch a native window via `ui.run(native=True)` (uses `pywebview`).
- **Async model:** Native `asyncio`. Event handlers, `ui.timer`, and lifecycle hooks all accept `async def` directly. A `TokenStreamBus` consumer is a one-liner: `async for delta in bus: log.push(delta)`.
- **Streaming:** Confirmed working. The 2023 GitHub issue #1128 ("token-by-token streaming") is resolved — modern idiom is `await element.update()` or `ui.label().set_text()` inside an async loop, and elements like `ui.log` / `ui.markdown` support incremental append. NiceGUI's own docs ship a chat example using OpenAI streaming.
- **Layout:** Quasar-based components (`ui.splitter`, `ui.row`, `ui.column`, `ui.tabs`) cover the three-panel layout cleanly. CSS/Tailwind classes are accepted directly.
- **Strengths:**
  - Single dependency adds the whole stack (FastAPI + Uvicorn + Quasar bundled).
  - No frontend build step, no Node toolchain.
  - Approval gate fits naturally: input bound to a NiceGUI element, on submit call `gate.resolve(...)` from an `async` handler.
  - `native=True` ships a desktop-window experience without code changes.
  - High Context7 benchmark score (80.84), 366 documented snippets, active 2026 releases (v3.x).
- **Weaknesses:**
  - Reactivity model is less obvious than Streamlit's "rerun the script" — multiple update mechanisms (`@ui.refreshable`, `ui.state`, direct mutation) can confuse newcomers.
  - Documentation cited as "less robust than Streamlit" in third-party surveys (Anvil 2025, Reddit 2025), though Context7 coverage is good.
- **License:** MIT.
- **Verdict:** **Best overall fit.** Async-native, lowest friction migration from the existing async TUI architecture, supports both browser and native-window deployment.

#### PySide6 + `qasync` / `PySide6.QtAsyncio`

- **Type:** Native desktop (Qt 6) bindings for Python.
- **Async model:** Qt has its own event loop. Two integration options:
  1. **`qasync`** (third-party, mature) — installs an asyncio loop policy that drives the Qt event loop, allowing `await` to work directly inside slot handlers.
  2. **`PySide6.QtAsyncio`** (official since Qt 6.6) — first-party asyncio integration; experimental but improving.
  3. **Bridge thread** — run the asyncio loop in a background `QThread`, dispatch via `asyncio.run_coroutine_threadsafe`, deliver results to the UI via Qt `Signal`s. This is the canonical pattern (see Python.org Async-SIG discussion, 2024) and is what the Textual TUI already does in spirit.
- **Streaming:** Trivial — connect a `Signal(str)` to a `QPlainTextEdit.appendPlainText` slot; emit from the asyncio bridge for each token.
- **Layout:** `QSplitter`, `QDockWidget`, `QStackedWidget` provide professional desktop layouts. Qt Designer for visual layout if desired.
- **Strengths:**
  - True native look-and-feel on every platform.
  - Mature, deeply documented, decades of stability (Qt is industry standard for scientific/engineering desktop apps — Anaconda, Spyder, Krita).
  - Excellent rich-text widgets (`QTextEdit`, `QTextCursor`) for streaming markdown/log.
  - No browser/HTTP indirection — lower latency for local pipelines.
- **Weaknesses:**
  - Heaviest dependency (~80–100 MB install).
  - asyncio integration always requires either `qasync` or a thread bridge — moderate complexity.
  - Steeper learning curve than NiceGUI for developers not already familiar with Qt.
  - Boilerplate-heavy compared to Python-first frameworks.
- **License:** **LGPLv3** (PySide6 is the LGPL Qt binding; `PyQt6` is GPL/commercial — prefer PySide6 for licence freedom).
- **Verdict:** Best choice if a polished native desktop application is the goal. Higher initial cost; long-term stability is unmatched.

### Tier 2 — Strong Alternatives

#### Chainlit

- **Type:** Browser-rendered, purpose-built for "conversational AI" / agentic LLM UIs. Built on FastAPI.
- **Async model:** Native `asyncio`. `@cl.on_message`, `@cl.on_chat_start`, `cl.Message(...).stream_token(...)` all `async`.
- **Streaming:** First-class — `cl.Message.stream_token(delta)` is the documented chat-streaming primitive.
- **Strengths:**
  - Built-in chat transcript, typing indicators, message feedback (👍/👎), chat history persistence, auth, and observability hooks — features the project would otherwise build by hand.
  - Step/sub-step visualisation maps naturally onto pipeline phases (`@cl.step` decorator).
  - Smallest amount of UI code to reach a working app.
- **Weaknesses:**
  - **Opinionated layout.** Chainlit assumes a chat-transcript shape. Multi-panel layouts (phase tracker on the left, wiki context on the right) are awkward — possible via "Elements" sidebar but constrained.
  - Less general-purpose than NiceGUI; if requirements grow beyond "agent chat with steps", you outgrow it.
  - Smaller community than Streamlit/NiceGUI.
- **License:** Apache 2.0.
- **Verdict:** Best fit if the GUI converges on a chat-style "talk to the story orchestrator" UX. Risky if you need rich custom dashboards.

#### Reflex (formerly Pynecone)

- **Type:** Python source compiled to a Next.js / React app.
- **Async model:** State methods can be `async def`; framework manages WebSocket transport.
- **Streaming:** Supported via async generator state methods that `yield` repeatedly; UI re-renders on each yield.
- **Strengths:**
  - Component model maps to React idioms; high ceiling for custom UI.
  - Strong styling story (Tailwind/Radix).
  - Production-grade scaling story (cloud-deploy ready).
- **Weaknesses:**
  - Compiles to Node/Next.js — adds a Node toolchain to the project.
  - Heaviest of the web-Python frameworks; overkill for a single-user local app.
  - State graph is more rigid than NiceGUI's direct mutation model.
- **License:** Apache 2.0.
- **Verdict:** Worth considering if the project later needs multi-user web hosting; over-engineered for the current single-user CLI/TUI use case.

### Tier 3 — Conditionally Useful

#### Flet

- **Type:** Python wrapper around Flutter; renders to web, desktop (via Flutter desktop), or mobile.
- **Async model:** Async-friendly handlers; reasonable but less mature than NiceGUI.
- **Strengths:** Beautiful Material-design UI out of the box; cross-platform single codebase including mobile.
- **Weaknesses:** Bundles a Flutter runtime (~tens of MB); ecosystem smaller than Qt or NiceGUI; documentation thinner; primary author's roadmap less predictable than NiceGUI's.
- **Verdict:** Pick only if mobile or Material-design aesthetic is a hard requirement.

#### Streamlit

- **Type:** Browser-rendered, "rerun the script" reactivity model.
- **Async model:** **Hostile to long-running async streams.** Every interaction reruns the script; streaming requires `st.write_stream` plus careful session-state choreography. A long-running pipeline orchestrator with mid-flight approval gates is awkward to express.
- **Verdict:** **Avoid for this project.** The script-rerun model conflicts with a stateful, long-running, async pipeline. Streamlit shines for stateless data dashboards, not for multi-phase orchestrated workflows.

#### Gradio

- **Type:** ML-demo-focused chat UI.
- **Verdict:** **Avoid.** Designed for `input → model → output` demos; insufficient flexibility for multi-panel orchestration UI.

#### Toga / BeeWare

- **Type:** Truly native cross-platform (delegates to native widgets per OS).
- **Verdict:** Promising philosophy but immature widget set vs. Qt; risky for a complex layout today.

#### Tkinter / wxPython / Kivy / Dear PyGui

- Not recommended. Tk is dated; wx mature but eclipsed by Qt; Kivy/Dear PyGui target games/touch UIs, not document-style streaming output.

### Emerging / Experimental

- **A2UI (Google, v0.8)** — declarative JSON-streamed UI protocol. Too early; revisit in 2027.
- **agex-ui** — agent-driven dynamic NiceGUI components. Niche; not a base framework choice.

---

## Integration Patterns (Reference)

### Pattern A — Async-native framework (NiceGUI, Chainlit, Reflex, Flet)

```python
# Pseudo-code: NiceGUI consumer
@ui.page('/')
async def main():
    log = ui.log().classes('h-96 w-full')
    bus = TokenStreamBus()
    gate = NiceGuiApprovalGate()
    asyncio.create_task(run_pipeline(story, gate, bus, wiki_bus))
    async for delta in bus:
        log.push(delta)
```

The orchestrator coroutine and the UI consumer share the same event loop. Approval gates resolve from `async` button handlers. **No threading required.**

### Pattern B — Non-asyncio framework with bridge thread (PySide6, Tk, wx)

The current `StoryWriterApp` already uses this pattern (`@work(thread=True)` → `asyncio.run(_run())` → bus drained on UI thread). For PySide6:

1. Create `QThread` running its own asyncio loop (`loop.run_forever()`).
2. Submit pipeline coroutine via `asyncio.run_coroutine_threadsafe(...)`.
3. Bus drainer also runs in that loop; for each token, emit a Qt `Signal` with the delta.
4. UI thread slot appends the delta to a `QPlainTextEdit`.
5. Approval-gate buttons (UI thread) call `loop.call_soon_threadsafe(gate.resolve, decision)`.

Mature reference: [bmitc/pyside-asyncio-prototype](https://github.com/bmitc/pyside-asyncio-prototype) (discussed on Python.org Async-SIG, 2024).

---

## Recommendations

1. **Prototype with NiceGUI first.** Lowest cost to validate the concept, async-native, can deploy as either a browser tab or a native window via `ui.run(native=True)`. Implementation effort is comparable to the existing Textual TUI; the `pipeline_primitives` are reusable verbatim.

2. **If desktop-native polish becomes a hard requirement,** migrate to PySide6 with `qasync`. Treat it as a second presentation adapter alongside the TUI and NiceGUI front-ends — the orchestrator and primitives stay unchanged.

3. **Keep the TUI.** It is the lightest-weight UX for headless/SSH/remote use and is already proven; a GUI complements rather than replaces it.

4. **Architectural guideline for any choice:** add the new front-end under `src/presentation/<gui-name>/`, mirroring the `tui/` package. Wire it through a new `story-writer gui` CLI subcommand that lazy-imports the GUI module (matching the existing TUI's lazy-import pattern in `src/presentation/cli/main.py`). This preserves the "GUI dependencies are optional" property already established by the TUI.

5. **Defer Reflex / Flet / Chainlit unless a specific need surfaces:**
   - Chainlit → revisit if UX collapses to a chat transcript with stepwise tool calls.
   - Reflex → revisit if multi-user hosted deployment is required.
   - Flet → revisit if mobile is required.

---

## Gaps / Uncertainties

- **NiceGUI's `native=True` (pywebview)** has historically had quirks on Linux Wayland — verify on the target dev environment before committing.
- **`PySide6.QtAsyncio`** is officially shipped but still labelled experimental in Qt 6.6/6.7 docs; `qasync` remains the safer choice today (2026) for production. Re-evaluate annually.
- **Streamlit + LangGraph human-in-the-loop** community examples exist (Streamlit forum, 2024–2026), but the consistent finding is that the script-rerun model fights stateful workflows — confirmed across multiple sources.
- **No source surveyed reports a frictionless `ApprovalGate`-style human-in-the-loop pattern in Streamlit/Gradio.** All examples rely on session-state hacks that the project's `asyncio.Future`-based gate can avoid entirely with NiceGUI/Chainlit/PySide6.

---

## Sources

- Anvil Works, "The Best Python Web App Frameworks in 2025" — https://anvil.works/articles/top-python-web-app
- Python GUIs (Martin Fitzpatrick), "Which Python GUI library should you use in 2026?" — https://www.pythonguis.com/faq/which-python-gui-library/
- Python GUIs, "PySide6 Concurrency" — https://www.pythonguis.com/topics/pyside6-concurrency/
- Python.org Async-SIG, "PySide6 + asyncio task prototype" — https://discuss.python.org/t/request-for-review-of-pyside6-qt-for-python-and-asyncio-task-prototype/49784
- Reflex blog, "Top Python Web Development Frameworks in 2025/2026" — https://reflex.dev/blog/python-comparison/
- GetStream, "The 3 Best Python Frameworks To Build UIs for AI Apps" — https://getstream.io/blog/ai-chat-ui-tools/
- Towards Data Science, "Rapid Prototyping of Chatbots with Streamlit and Chainlit" — https://towardsdatascience.com/rapid-prototyping-of-chatbots-with-streamlit-and-chainlit/
- Ploomber, "A Survey of Python Frameworks" — https://ploomber.io/blog/survey-python-frameworks/
- JetBrains, "The Most Popular Python Frameworks and Libraries in 2025" — https://blog.jetbrains.com/pycharm/2025/09/the-most-popular-python-frameworks-and-libraries-in-2025-2/
- MatterAI, "Building Real-Time AI Apps: WebSockets and LLM Streaming" — https://www.matterai.so/guides/building-real-time-ai-applications-with-websockets-and-streaming-responses
- NiceGUI documentation via Context7 (`/zauberzeug/nicegui`, v3.6.0) — async timers, refreshable UI, streaming-download patterns
- Stack Overflow, "Trouble connecting an async function to a PySide6 button signal" — https://stackoverflow.com/questions/76413536
- GitHub issue zauberzeug/nicegui#1128 — historical token-streaming question
- Project source: `src/presentation/pipeline_primitives.py`, `docs/features/textual-tui.md`, `pyproject.toml`
