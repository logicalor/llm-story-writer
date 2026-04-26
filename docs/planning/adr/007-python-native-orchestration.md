# ADR 007: Python-Native Orchestration and TUI (Supersedes ADR 001)

**Date:** 2026-04-24
**Status:** Proposed — supersedes [ADR 001](./001-hybrid-agent-tool-architecture.md)

## Context

ADR 001 introduced a hybrid agent-tool architecture running inside OpenCode (a TypeScript/Node.js AI agent harness). Markdown-defined agents orchestrated Python tool wrappers, which in turn called Python domain scripts via subprocess.

In practice, the OpenCode harness has produced recurring failure modes:

- **Nested dispatch instability.** Multi-level agent dispatch accumulates conversation context and has historically triggered VS Code UI freezes. A previous workaround flattened dispatch depth (PR #70) but the underlying architecture remains fragile.
- **Triple-language overhead.** Agents in Markdown, wrappers in TypeScript, logic in Python. Every tool call crosses two language boundaries and one subprocess boundary — no shared types, no shared error handling, no shared logging.
- **Subprocess serialization.** Every orchestrator → tool call re-encodes arguments and outputs through JSON over stdio. Streaming outputs are lost. Python exceptions become opaque stderr text.
- **Non-deterministic dispatch.** OpenCode's `task()` dispatch depends on the orchestrator LLM correctly emitting tool-call-formatted requests. Smaller quantized local models (e.g., Gemma-4 26B) do not reliably support function calling, making dispatch itself a source of pipeline failures.
- **No streaming to the user.** OpenCode's TUI surfaces orchestrator narration but does not stream token-by-token LLM output from subagent generation tasks, which is the operator's most important real-time signal during chapter writing.

A three-model research synthesis (see `.github/research/python-native-migration-2026-04-24.md`) evaluated alternatives. The story generation pipeline is fundamentally a sequential, deterministic, phase-gated workflow — not a cyclic autonomous agent graph. Heavyweight frameworks (CrewAI, AutoGen, LangGraph) reintroduce most of OpenCode's complexity without solving its core problems.

## Decision

**Eliminate OpenCode. Make Python the full harness.**

1. **Orchestration:** Plain Python. Each former OpenCode agent becomes a Python async class or function. Pipeline phases are sequential async calls into the existing `src/application/services/` layer. Approval gates are `asyncio` awaits against a TUI-provided future.
2. **TUI:** Textual (`>=6.0,<7.0`). `@work(thread=True)` workers wrap pipeline execution; `call_from_thread()` streams token deltas into a `RichLog` widget. CSS grid layout provides status panel, streaming output panel, and approval input.
3. **LLM client:** `openai.AsyncOpenAI` with `base_url="http://127.0.0.1:1234/v1"` and `api_key="lm-studio"`. Streaming enabled by default. Wrapped behind the existing `ModelProvider` interface in `src/infrastructure/providers/`.
4. **Agent definitions:** The existing `.opencode/agents/*.md` files are relocated to `prompts/agents/` and loaded at startup as system prompt strings (frontmatter stripped). No content changes.
5. **Tool execution:** TypeScript wrappers in `.opencode/tools/` are deleted. The Python orchestrator imports and calls `src/tools/*.py` and `src/application/services/*.py` directly, in-process.
6. **Structured handoffs:** Pipeline phases communicate via typed dataclasses/Pydantic models (`OutlineResult`, `ChapterDraft`, `WikiUpdateBatch`), not free-form text or chat histories.

## Consequences

### Positive

- **Single language.** Python end-to-end. One error model, one logging stack, one type system.
- **Streaming-first TUI.** Token-by-token display of chapter generation is a baseline capability, not an add-on.
- **No function-calling dependency.** Orchestration is deterministic Python code — pipeline execution is independent of whether the local LLM supports tool-call format.
- **Clean architecture preserved.** `src/domain/`, `src/application/`, `src/infrastructure/` layers are unchanged. Only `src/presentation/` gains new modules (pipeline runner + TUI).
- **Simpler debugging.** Full Python traceback across all layers. `pdb`/`ipdb` work throughout.
- **Smaller surface area.** No Node.js, no npm, no vitest, no TypeScript compiler, no OpenCode binary.

### Negative

- **Approval gates and pause/resume must be hand-implemented.** No framework-provided `interrupt()` primitive. Mitigation: `asyncio.Future` + Textual `Input` widget — well-understood pattern.
- **Durable resumable execution not free.** The existing JSON savepoint system handles this today; no regression, but no upgrade either. Deferred option: adopt LangGraph's Functional API (`@entrypoint`/`@task`) if durable graph execution later becomes a first-class requirement.
- **Textual learning curve.** Reactive widget model and async worker conventions are unfamiliar to most contributors. Mitigation: confine Textual surface to `src/presentation/tui.py`.
- **Loss of agent-inspectable narration.** OpenCode's orchestrator narration in Markdown agents becomes Python log output. The TUI must surface pipeline progress explicitly via status widgets — not implicitly via LLM narration.

### Neutral

- **Agent system prompts remain Markdown.** Easy to edit, version, and diff. Loaded at startup; hot-reload is optional future work.
- **ChromaDB, JSON state, savepoints unchanged.** The storage layer is orthogonal to the harness change.
- **Streaming API choice is reversible.** `httpx` direct calls are a fallback if the `openai` SDK becomes a constraint. The `ModelProvider` interface isolates this choice.

## Supersession

This ADR supersedes [ADR 001](./001-hybrid-agent-tool-architecture.md). The hybrid agent-tool architecture is retired. The underlying principle — agents make creative decisions, deterministic code handles mechanics — is preserved, but "agent" now means "Python async function that issues a prompt to an LLM," not "Markdown document dispatched by OpenCode."

ADRs 002–006 remain in force. Context window management, ChromaDB retrieval, progressive wiki memory, and the OpenAI-compatible provider are all storage- or algorithm-level decisions orthogonal to the harness.

## Addendum — Implementation Divergence (2026-04-26, ADR 008)

During the Python-native migration, all orchestrator agents were implemented to call `provider.stream_text()` directly rather than routing through `src/application/services/`. This diverged from the intent stated in Decision point 5 above (*"the Python orchestrator imports and calls `src/application/services/*.py` directly, in-process"*).

A formal architecture review (issue #188) examined the gap and issued [ADR 008](./008-retire-application-services-layer.md), which formally retires the services layer as dead code. The exception is `critique_parser.py`, which has active callers in `src/tools/critique_runner.py` and is retained.
