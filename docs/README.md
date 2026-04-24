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

The active runtime is intentionally small and OpenCode-first:

- **Python runtime**: install from `requirements.txt`; it is the only supported dependency manifest for the active project and includes `requests`, `openai`, `chromadb`, `pyyaml`, and `llm-output-parser`
- **LLM integration**: Supported provider keys are `openai_compatible` and `openai_async`; all runtime traffic goes through OpenAI-compatible `/v1` endpoints rather than LangChain-specific adapters
- **Async provider path**: `src/infrastructure/providers/openai_async_provider.py` adds an `AsyncOpenAI`-backed `ModelProvider` implementation for Python-native streaming flows, while `OpenAICompatibleProvider` remains in place for existing synchronous paths
- **Tool wiring**: the Python-native orchestrator and tool modules now run in-process; `.opencode/tools/` remains only as a placeholder directory with `.gitkeep`
- **Python-native migration foundation**: agent system prompts now live in `prompts/agents/`, with shared loading logic in `src/infrastructure/prompts/agent_prompt_loader.py` and typed orchestration payloads in `src/application/pipeline/handoffs.py`
- **Pipeline presentation primitives**: `src/presentation/pipeline_primitives.py` adds transport-agnostic approval gates plus token and wiki context buses for both headless runners and future Textual UI integration
- **Headless orchestrator slice**: `src/presentation/orchestrator.py` now runs the implemented Python-native phase sequence (`init → outline → characters → settings → chapter-loop → final-edit → assembly`) and persists `PipelineState` savepoints for resume support
- **Repository cleanup**: the temporary `legacy/` archive, duplicate root helper scripts, and obsolete root markdown summaries were removed after migration cleanup, so current documentation should point only to active files under `docs/`, `prompts/`, `src/`, and `tests/`

See [Legacy Dependency Cleanup](./features/legacy-dependency-cleanup.md) for the full before/after summary and maintenance guidance.

## Tools

- [Tools Reference](./tools.md) — Python-native tool architecture, `story-writer` console entry point, retained `src/tools/` CLIs, and current tool inventory
- [Comprehensive Manual](./manual.md) — End-to-end system guide covering setup, architecture, usage, tools, troubleshooting, and operational workflows

## Testing

- [Integration Tests](./testing/integration-tests.md) — Live end-to-end pipeline test for story generation with wiki support, runtime expectations, LLM endpoint configuration, and manual verification steps

## Features

- [OpenAI Async Provider](./features/openai-async-provider.md) — AsyncOpenAI-backed streaming `ModelProvider`, dependency requirements, and migration relationship to the existing sync provider
- [Python-Native Foundation](./features/python-native-foundation.md) — Agent prompt relocation, frontmatter-stripping loader, typed pipeline handoff dataclasses, and the `story-writer` CLI packaging/dispatch path for Issues #158, #161, and #162
- [Pipeline Primitives](./features/pipeline-primitives.md) — Transport-agnostic approval gates plus token and wiki context event buses for the Python-native orchestrator
- [Legacy Dependency Cleanup](./features/legacy-dependency-cleanup.md) — Current runtime dependency model, removed migration leftovers, and guardrails for keeping the active stack lean
- [Story Orchestrator](./features/story-orchestrator.md) — Implemented headless Python pipeline runner, approval-gate semantics, agent callable pattern, and `PipelineState` savepoint/status behavior
- [Story Planner](./features/story-planner.md) — Phase 2.5 narrative arc analysis subagent: critic pass, arc prompt set, advisory verdicts, and approval-gate integration
- [Chapter Outline Expander](./features/chapter-outline-expander.md) — Phase 7a subagent that expands all chapter outlines and carries structured handoff continuity between chapters
- [Prose Quality Passes](./features/prose-quality-passes.md) — `prose-scrubber` and `final-editor` pipeline stages, config flags, scope constraints, and tool usage
- [Wiki Maintainer](./features/wiki-maintainer.md) — Wiki maintenance subagent: tool-delegated extraction via `wiki-extract`, confidence scoring, detail levels, alias identification, and chapter boundary procedures
- [Custom Commands](./features/custom-commands.md) — Seven slash commands for the OpenCode TUI: `/new-story`, `/continue`, `/regenerate`, `/savepoint`, `/status`, `/settings`, `/wiki`
- [Compaction Plugin](./features/compaction-plugin.md) — OpenCode plugin that injects story continuity context into session compaction summaries

## Planning

- [PRD: Python-Native Orchestration and TUI](./planning/python-native-migration/prd.md) — Product requirements and current implementation status for the Python-native migration
- [PRD: OpenCode Migration](./planning/opencode-migration/prd.md) — Full product requirements for the agentic architecture migration
- [Migration Tasks](./planning/opencode-migration/tasks.md) — Task breakdown and completion status

### Architecture Decision Records

- [ADR 001: Hybrid Agent-Tool Architecture](./planning/adr/001-hybrid-agent-tool-architecture.md)
- [ADR 002: Context Window Budget Strategy](./planning/adr/002-context-window-budget-strategy.md)
- [ADR 003: ChromaDB Replaces pgvector](./planning/adr/003-chromadb-replaces-pgvector.md)
- [ADR 004: Progressive Wiki Memory System](./planning/adr/004-progressive-wiki-memory-system.md)
- [ADR 005: Hybrid Wiki Context Retrieval Pipeline](./planning/adr/005-hybrid-wiki-context-retrieval-pipeline.md)
- [ADR 006: Replace Ollama SDK with Generic OpenAI-Compatible REST Provider](./planning/adr/006-openai-compatible-provider.md)
