# PRD: Python-Native Orchestration and TUI

> Replace the OpenCode (TypeScript/Node.js) agent harness with a pure-Python orchestration layer, a Textual-based TUI with streaming output, and direct in-process tool execution.

**Date:** 2026-04-24
**Author:** Planner agent
**Status:** Draft
**Related:** ADR 007 (to be written) supersedes [ADR 001](./adr/001-hybrid-agent-tool-architecture.md); research synthesis at `.github/research/python-native-migration-2026-04-24.md`.

## Problem Statement

The current system uses OpenCode as its harness. Agents are Markdown files dispatched via `task()`; tools are TypeScript wrappers in `.opencode/tools/` that call Python scripts via subprocess. The real domain logic is already Python — OpenCode contributes dispatch, terminal UI, and cross-language plumbing.

This architecture has produced a steady stream of operational problems: VS Code UI freezes from nested dispatch, non-deterministic tool-call dispatch on quantized local models, loss of streaming output through subprocess boundaries, and a triple-language debugging surface (Markdown → TypeScript → Python). Streaming token-by-token LLM output during chapter generation — a non-negotiable operator signal — cannot cleanly be surfaced through the current stack.

A three-model research synthesis confirms the story generation pipeline is sequential and deterministic, not a cyclic autonomous agent system. The OpenCode harness is over-fit for the workload. Replacing it with a plain Python pipeline and a Textual TUI eliminates the failure classes above without reducing functionality.

## Goals

1. Eliminate all OpenCode/Node.js/TypeScript from the runtime — `.opencode/`, `opencode.json`, `package.json`, `tsconfig.json`, `vitest.config.ts`, all `.ts` files under the project root.
2. Preserve all existing domain logic (`src/domain/`, `src/application/`, `src/infrastructure/`) without rewrites.
3. Preserve all existing Markdown agent system prompts by relocating them to `prompts/agents/` and loading via a frontmatter-stripping loader.
4. Build a Textual TUI that streams LLM token output in real time, displays pipeline phase progress, and handles human approval gates mid-pipeline.
5. Build a Python orchestrator that executes the story generation pipeline phases sequentially, calling `src/application/services/` directly in-process.
6. Support both interactive mode (TUI with approval gates) and batch/headless mode (CLI, no approval gates, auto-proceed).
7. Maintain full test coverage: all existing `pytest` tests pass after migration; new orchestrator and TUI layers have their own tests.

## Non-Goals

- **Rewriting the domain logic.** `src/domain/`, `src/application/services/`, and storage layers are preserved as-is.
- **Adopting LangGraph, CrewAI, AutoGen, or Pydantic AI as the orchestration framework.** Documented as deferred upgrade paths only.
- **Changing the prompt templates in `prompts/`.** Content is preserved verbatim.
- **Changing the LLM endpoint or local inference stack.** LM Studio at `http://127.0.0.1:1234/v1` remains the primary target.
- **Building a web UI.** Textual TUI only. `textual-web` is a deferred option.
- **Durable, resumable graph execution beyond the existing JSON savepoint system.** Current savepoint semantics are preserved; no checkpointer upgrade.

## User Stories

### Story Writer (interactive operator)

- As a writer, I want to launch the TUI and see pipeline phases progressing in real time so that I know what the system is doing.
- As a writer, I want to see chapter prose streaming token-by-token as it is generated so that I can spot quality problems early.
- As a writer, I want the pipeline to pause at outline-approval and chapter-approval gates so that I can approve, reject, or request revisions before proceeding.
- As a writer, I want to resume a story from its latest savepoint so that I can recover from interruption without re-running earlier phases.

### Batch Operator (unattended runs)

- As a batch operator, I want to run the full pipeline headlessly via CLI so that I can generate stories unattended.
- As a batch operator, I want all approval gates to auto-accept in batch mode so that the pipeline runs end-to-end.
- As a batch operator, I want clear exit codes and structured log output so that I can integrate with automation.

### Maintainer (developer)

- As a maintainer, I want a single Python codebase with no TypeScript/Node.js build step so that I can contribute without installing a second toolchain.
- As a maintainer, I want full Python tracebacks across all layers when errors occur so that I can debug efficiently.
- As a maintainer, I want pipeline phases to be independently testable Python functions so that I can write focused unit tests.

## Proposed Solution

## Current Implementation Status

Issue #158 / PR #167 implemented the first foundation slice of this migration:

- [x] Task 1 foundation complete: all eleven agent prompts were relocated to `prompts/agents/`
- [x] Shared Python loader added at `src/infrastructure/prompts/agent_prompt_loader.py`
- [x] Typed pipeline handoff package added at `src/application/pipeline/`
- [x] `PipelineState` now supports JSON-friendly `to_dict()` / `from_dict()` persistence helpers for savepoints

### Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│  src/presentation/tui.py       (Textual App)         │
│   ├─ Status panel              (phase progress)      │
│   ├─ Output panel (RichLog)    (token stream)        │
│   └─ Input widget              (approval gates)      │
└─────────────────┬────────────────────────────────────┘
                  │ @work(thread=True) + call_from_thread()
┌─────────────────▼────────────────────────────────────┐
│  src/presentation/orchestrator.py                    │
│   ├─ Phase runner              (sequential async)    │
│   ├─ Approval gate primitive   (asyncio.Future)      │
│   ├─ Streaming token bus       (async queue)         │
│   └─ Typed handoff objects     (dataclasses)         │
└─────────────────┬────────────────────────────────────┘
                  │ direct in-process calls (no subprocess)
┌─────────────────▼────────────────────────────────────┐
│  src/application/services/     (UNCHANGED)           │
│  src/application/strategies/   (UNCHANGED)           │
│  src/domain/                   (UNCHANGED)           │
│  src/infrastructure/           (+ AsyncOpenAI client)│
│  src/tools/                    (UNCHANGED)           │
└──────────────────────────────────────────────────────┘
```

### Orchestration

- Each OpenCode agent becomes a Python async function or class in `src/presentation/agents/`. Each agent owns: (a) its system prompt (loaded from `prompts/agents/<name>.md`), (b) its dispatch of relevant services, (c) its typed handoff output.
- Pipeline phases are sequential `await` calls in `src/presentation/orchestrator.py`. Phases: Init → Outline → Narrative Arc Analysis → Character Sheets → Settings → Chapter Loop → Final Edit → Assembly.
- Approval gates are `asyncio.Future` objects. The orchestrator awaits the future; the TUI resolves it when the user submits input. In batch mode, a null-gate implementation resolves futures immediately.
- Streaming: the LLM provider yields token deltas onto an `asyncio.Queue`. The TUI's worker drains the queue and writes to the `RichLog` via `call_from_thread()`. The orchestrator is agnostic to consumer.

### TUI (Textual)

- Single-screen app with CSS grid layout. Left column: phase list with progress indicators. Right column: streaming output `RichLog`. Footer: approval `Input` widget (hidden until a gate is active). Header: story title and savepoint indicator.
- Keybindings: `Ctrl+C` graceful cancel (cancels worker, writes savepoint, exits), `Ctrl+S` manual savepoint, `Enter` submit approval.
- `@work(thread=True)` worker runs the orchestrator. A thin bridge uses `call_from_thread()` to forward token deltas, phase transitions, and gate prompts into Textual widgets.

### LLM Client

- Add `src/infrastructure/providers/openai_async_provider.py`: `AsyncOpenAI` wrapper implementing the existing `ModelProvider` interface with full streaming support.
- Wire at startup using existing `config.yml` keys (`provider.base_url`, `provider.models.*`). Reuse existing `src/config/` loader.
- The current synchronous `OpenAICompatibleProvider` is retained as a fallback for code paths that cannot be refactored in the first cut; marked for removal in a follow-up.

### Agent Prompts

- Relocate `.opencode/agents/*.md` → `prompts/agents/*.md` preserving filenames.
- Add `src/infrastructure/prompts/agent_prompt_loader.py`: loads a Markdown file, strips YAML frontmatter, returns body as a string.
- Orchestrator agent functions call this loader at module import time.

### Tool Execution

- Delete `.opencode/tools/*.ts`. The Python scripts in `src/tools/*.py` are already the real implementation.
- Orchestrator imports services directly: `from application.services.chapter_service import ChapterService`.
- The `src/tools/*.py` CLI entry points are retained as standalone scripts for ad-hoc shell invocation.

### CLI Entry Points

- `src/presentation/cli/main.py`: currently a stub that raises `NotImplementedError`. Replace with argparse-based entry point.
  - `story-writer tui [--story <name>]` → launch Textual app.
  - `story-writer run --story <name> [--batch]` → headless pipeline run.
  - `story-writer resume --story <name>` → resume from latest savepoint.
- `pyproject.toml` exposes `story-writer` console script.

### Database / Storage

No schema changes. JSON savepoints, JSON story state, and ChromaDB collections are unchanged.

## Acceptance Criteria

- [ ] All files under `.opencode/`, all `.ts` files under the project root, `opencode.json`, `package.json`, `tsconfig.json`, and `vitest.config.ts` are removed from the repository.
- [x] All `.opencode/agents/*.md` files are relocated to `prompts/agents/` with unchanged content.
- [x] Typed handoff dataclasses exist under `src/application/pipeline/handoffs.py` with JSON round-trip support for pipeline savepoints.
- [ ] `python -m src.presentation.cli.main tui --story <name>` launches a Textual app with status panel, streaming output panel, and approval input widget.
- [ ] Launching a story run in the TUI streams LLM token output into the output panel in real time (visibly token-by-token, not all-at-once).
- [ ] The TUI pauses at outline and chapter approval gates. Typing `approve` / `reject` / `revise <feedback>` resumes or adjusts the pipeline.
- [ ] `python -m src.presentation.cli.main run --story <name> --batch` runs the full pipeline end-to-end without any prompts and exits with code 0 on success.
- [ ] `python -m src.presentation.cli.main resume --story <name>` resumes from the latest savepoint.
- [ ] The existing `pytest` test suite passes without modifications to domain or application layer tests (integration tests may be re-pointed at the new CLI).
- [ ] New tests exist for: agent prompt loader (frontmatter stripping), async OpenAI provider (streaming), orchestrator phase runner (sequential execution + approval gate resolution), TUI bridge (token forwarding to widget).
- [ ] A full end-to-end integration test generates a two-chapter story in under 10 minutes against LM Studio.
- [ ] `AGENTS.md`, `README.md`, and `docs/` contain no references to OpenCode, `opencode.json`, `.opencode/`, or the TypeScript tool layer.
- [ ] `ruff check .`, `ruff format --check .`, and `mypy src/` all pass cleanly.

## Resolved Decisions

- **Model identification.** Model name stays pinned in `config.yml` (status quo). The provider layer may change later, so the interface keeps a single `model` parameter passed through from config — no auto-discovery against `/v1/models` at startup.
- **Live wiki context in TUI.** In scope. The TUI gains a third panel (or toggleable overlay) showing the wiki context currently assembled for the phase being executed: active entity matches, wikilink traversal results, detail-level selections. Implemented in Task 8.
- **`.opencode/plugins/story-compaction.ts` retention.** Removed. The plugin parses YAML frontmatter from agent Markdown to estimate token budgets for OpenCode's conversation-history compaction. In a Python harness there is no free-floating orchestrator conversation to compact — each pipeline phase is a bounded, direct LLM call. No Python port required.
- **`.opencode/_run.ts` retention.** Removed. It is pure subprocess-invocation boilerplate for running Python tools from OpenCode; obsolete once the orchestrator calls Python in-process.

## Related

- Research synthesis: `.github/research/python-native-migration-2026-04-24.md`
- ADR 007 (to be written)
- ADR 001 (superseded): `docs/planning/adr/001-hybrid-agent-tool-architecture.md`
- Prior migration PRD (superseded direction): `docs/planning/opencode-migration/prd.md`
