# Documentation

> Index for llm-story-writer project documentation.

## Architecture

- [Architecture Notes](../.github/notes/architecture.md) — System architecture, layer structure, pipeline flow, prompt template categories

## Storage

The project uses **ChromaDB** for vector storage and RAG (Retrieval-Augmented Generation). ChromaDB is a lightweight, file-based vector database that requires no server process or Docker setup.

- **Local-first**: No PostgreSQL, pgvector, or Docker Compose required
- **Per-story collections**: Each story has its own isolated ChromaDB collection (`story-{story-name}`)
- **Storage location**: `.chromadb/stories/{story-name}/`
- **Indexed content**: Outline chunks, chapter content, character sheets, setting sheets, and recaps

### RAG Access

All RAG queries route through the `rag-query` tool (see [Tools Reference](./tools.md)). The legacy application-layer `RAGService` has been removed from the repository.

See [ADR 003: ChromaDB Replaces pgvector](./planning/adr/003-chromadb-replaces-pgvector.md) for the full migration rationale.

## Runtime Stack

The active runtime is intentionally small and Python-native:

- **Python runtime**: install from `pyproject.toml`; dependencies are declared there and include `requests`, `openai`, `chromadb`, `pyyaml`, and `llm-output-parser`
- **LLM integration**: Supported provider keys are `openai_compatible` and `openai_async`; all runtime traffic goes through OpenAI-compatible `/v1` endpoints rather than LangChain-specific adapters
- **Async provider path**: `src/infrastructure/providers/openai_async_provider.py` adds an `AsyncOpenAI`-backed `ModelProvider` implementation for Python-native streaming flows, while `OpenAICompatibleProvider` remains in place for existing synchronous paths
- **Tool wiring**: the Python-native orchestrator and tool modules now run in-process with no `.opencode/` or Node.js wrapper layer remaining in the repository
- **Python-native migration foundation**: agent workflow specifications for OpenCode and Copilot runtimes live in `prompts/agents/`, reusable skill references live in `prompts/skills/`, and Python-native agents load direct-generation prompts via `PromptLoader` from `src/infrastructure/prompts/prompt_loader.py` with typed orchestration payloads in `src/application/pipeline/handoffs.py`
- **Pipeline presentation primitives**: `src/presentation/pipeline_primitives.py` adds transport-agnostic approval gates plus token and wiki context buses for both headless runners and the Textual TUI
- **Headless orchestrator slice**: `src/presentation/orchestrator.py` now runs the implemented Python-native phase sequence (`init → story-foundation → outline → [outline gate] → narrative-arc → characters → settings → wiki-init → wiki-bootstrap → chapter-loop → final-edit → assembly`), persists `PipelineState` savepoints for resume support, stores advisory arc results in `state.arc_result`, generates character and setting sheet JSON files under `stories/<story>/characters/` and `stories/<story>/settings/` with populated `summary`, `abridged`, and `chunks` fields, records per-chapter sheet evolution in `state.evolved_sheets`, writes approved chapter files to `stories/<story>/chapters/chapter_{N}.md`, emits `stories/<story>/output/story_edited.md` when Phase 9 runs, and assembles `stories/<story>/output/story.md` from the final `state.approved_chapters`
- **Interactive Textual TUI**: `src/presentation/tui/app.py` adds `StoryWriterApp`, a three-panel terminal UI with live token streaming, wiki context, and approval gates launched through `story-writer tui`
- **Repository cleanup**: the temporary `legacy/` archive, duplicate root helper scripts, and obsolete root markdown summaries were removed after migration cleanup, so current documentation should point only to active files under `docs/`, `prompts/`, `src/`, and `tests/`

The repository also carries a project-level Opencode configuration for migration work. That agent runtime now has a full 24-agent migrated inventory in `.opencode/agents/`, uses OpenRouter model IDs in `opencode.json`, and keeps developer-specific OpenRouter credentials plus Tavily and Context7 MCP entries in user-level Opencode config. The original Copilot agent definitions are preserved in `.github/agents-copilot/` and the intermediate OpenRouter migration set in `.github/agents-openrouter/`; neither directory was deleted. See [Opencode Runtime Configuration](./features/opencode-runtime.md).

See [Legacy Dependency Cleanup](./features/legacy-dependency-cleanup.md) for the full before/after summary and maintenance guidance.

## Tools

- [Tools Reference](./tools.md) — Python-native tool architecture, `story-writer` console entry point, retained `src/tools/` CLIs, and current tool inventory
- [Comprehensive Manual](./manual.md) — End-to-end system guide covering setup, architecture, usage, tools, troubleshooting, and operational workflows

## Testing

- [Integration Tests](./testing/integration-tests.md) — Live integration suite covering wiki E2E, headless batch E2E, `slow` marker usage, LLM endpoint requirements, and manual verification steps

## Features

- [Opencode Runtime Configuration](./features/opencode-runtime.md) — Project-level OpenRouter model registry, complete 24-agent migration inventory, and developer-local OpenRouter, Tavily, and Context7 setup
- [OpenAI Async Provider](./features/openai-async-provider.md) — AsyncOpenAI-backed streaming `ModelProvider`, dependency requirements, and migration relationship to the existing sync provider
- [Python-Native Foundation](./features/python-native-foundation.md) — Agent prompt relocation, `PromptLoader`-based direct-generation prompt loading, typed pipeline handoff dataclasses, and the `story-writer` CLI packaging/dispatch path for Issues #158, #161, and #162
- [Pipeline Primitives](./features/pipeline-primitives.md) — Transport-agnostic approval gates plus token and wiki context event buses for the Python-native orchestrator
- [Legacy Dependency Cleanup](./features/legacy-dependency-cleanup.md) — Current runtime dependency model, removed migration leftovers, and guardrails for keeping the active stack lean
- [Story Orchestrator](./features/story-orchestrator.md) — Implemented headless Python pipeline runner, advisory metadata checkpoints, narrative-arc and final-edit phases, approval-gate semantics, enriched character/setting sheet generation, per-chapter sheet evolution, chapter prompt context loading, and `PipelineState` savepoint/status behavior
- [Recap Writer Agent](./features/recap-writer-agent.md) — Post-approval chapter recap pipeline, recap persistence, flag-controlled short path, and advisory failure semantics
- [Story Planner](./features/story-planner.md) — Phase 2.5 narrative-arc agent: advisory streamed assessment, `ArcAnalysisResult`, and `arc_analysis_complete` persistence
- [Textual TUI](./features/textual-tui.md) — Interactive `StoryWriterApp` terminal UI, thread bridge architecture, layout, keybindings, and approval flow
- [Chapter Outline Expander](./features/chapter-outline-expander.md) — Phase 7a subagent that expands all chapter outlines and carries structured handoff continuity between chapters
- [Prose Quality Passes](./features/prose-quality-passes.md) — `prose-scrubber` and `final-editor` pipeline stages, config flags, scope constraints, and tool usage
- [Direct-Generation Prompts](./features/direct-generation-prompts.md) — Tool-free prompt templates and agent integration for Python-native creative generation
- [Wiki Maintainer](./features/wiki-maintainer.md) — Wiki maintenance subagent: tool-delegated extraction via `wiki-extract`, confidence scoring, detail levels, alias identification, and chapter boundary procedures
- [Custom Commands](./features/custom-commands.md) — Historical note on the retired OpenCode slash-command surface; reusable `continue` and `regenerate` prompt bodies were preserved under `prompts/agents/`
- [Compaction Plugin](./features/compaction-plugin.md) — Historical note on the removed OpenCode session-compaction plugin

## Planning

- [PRD: Python-Native Orchestration and TUI](./planning/python-native-migration/prd.md) — Product requirements and current implementation status for the Python-native migration
- [PRD: OpenCode Migration](./planning/opencode-migration/prd.md) — Full product requirements for the agentic architecture migration
- [Migration Tasks](./planning/copilot-to-opencode-migration/tasks.md) — Task breakdown and completion status for the Copilot-to-Opencode agent migration

### Architecture Decision Records

- [ADR 001: Hybrid Agent-Tool Architecture](./planning/adr/001-hybrid-agent-tool-architecture.md)
- [ADR 002: Context Window Budget Strategy](./planning/adr/002-context-window-budget-strategy.md)
- [ADR 003: ChromaDB Replaces pgvector](./planning/adr/003-chromadb-replaces-pgvector.md)
- [ADR 004: Progressive Wiki Memory System](./planning/adr/004-progressive-wiki-memory-system.md)
- [ADR 005: Hybrid Wiki Context Retrieval Pipeline](./planning/adr/005-hybrid-wiki-context-retrieval-pipeline.md)
- [ADR 006: Replace Ollama SDK with Generic OpenAI-Compatible REST Provider](./planning/adr/006-openai-compatible-provider.md)
- [ADR 007: Python-Native Orchestration and TUI](./planning/adr/007-python-native-orchestration.md)
- [ADR 008: Retire the Application Services Layer](./planning/adr/008-retire-application-services-layer.md)
- [ADR 009: Opencode as Primary Agent Runtime](./planning/adr/009-opencode-as-primary-agent-runtime.md)
