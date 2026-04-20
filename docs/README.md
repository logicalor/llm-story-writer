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

- **Python runtime**: install from `requirements.txt`; it is the only supported dependency manifest for the active project and includes `requests`, `chromadb`, `pyyaml`, and `llm-output-parser`
- **LLM integration**: Supported provider keys are `openai_compatible`, `ollama`, `lm_studio`, and `llama_cpp`; all runtime traffic goes through OpenAI-compatible `/v1` endpoints rather than LangChain-specific adapters
- **Tool wiring**: OpenCode loads TypeScript wrappers directly; no legacy `dependency-injector` container remains in the repository
- **Repository cleanup**: the temporary `legacy/` archive, duplicate root helper scripts, and obsolete root markdown summaries were removed after migration cleanup, so current documentation should point only to active files under `docs/`, `prompts/`, `src/`, and `tests/`

See [Legacy Dependency Cleanup](./features/legacy-dependency-cleanup.md) for the full before/after summary and maintenance guidance.

## Tools

- [Tools Reference](./tools.md) — Tool architecture pattern, prompt-loader, story-state, savepoint-mgr, character-mgr, setting-mgr, recap-manager, outline-generator, scene-writer, critique-runner, wiki-init, wiki-read, wiki-search, wiki-snapshot, wiki-update, and wiki-lint tools, guide for adding new tools
- [Comprehensive Manual](./manual.md) — End-to-end system guide covering setup, architecture, usage, tools, troubleshooting, and operational workflows

## Testing

- [Integration Tests](./testing/integration-tests.md) — Live end-to-end pipeline test for story generation with wiki support, runtime expectations, LLM endpoint configuration, and manual verification steps

## Features

- [Legacy Dependency Cleanup](./features/legacy-dependency-cleanup.md) — Current runtime dependency model, removed migration leftovers, and guardrails for keeping the active stack lean
- [Story Orchestrator](./features/story-orchestrator.md) — Primary pipeline controller agent: 9-phase story generation lifecycle, quality gates, wiki lifecycle, savepoint strategy, subagent delegation
- [Wiki Maintainer](./features/wiki-maintainer.md) — Wiki maintenance subagent: entity extraction, confidence scoring, detail levels, alias identification, chapter boundary procedures
- [Custom Commands](./features/custom-commands.md) — Seven slash commands for the OpenCode TUI: `/new-story`, `/continue`, `/regenerate`, `/savepoint`, `/status`, `/settings`, `/wiki`
- [Compaction Plugin](./features/compaction-plugin.md) — OpenCode plugin that injects story continuity context into session compaction summaries

## Planning

- [PRD: OpenCode Migration](./planning/opencode-migration/prd.md) — Full product requirements for the agentic architecture migration
- [Migration Tasks](./planning/opencode-migration/tasks.md) — Task breakdown and completion status

### Architecture Decision Records

- [ADR 001: Hybrid Agent-Tool Architecture](./planning/adr/001-hybrid-agent-tool-architecture.md)
- [ADR 002: Context Window Budget Strategy](./planning/adr/002-context-window-budget-strategy.md)
- [ADR 003: ChromaDB Replaces pgvector](./planning/adr/003-chromadb-replaces-pgvector.md)
- [ADR 004: Progressive Wiki Memory System](./planning/adr/004-progressive-wiki-memory-system.md)
- [ADR 005: Hybrid Wiki Context Retrieval Pipeline](./planning/adr/005-hybrid-wiki-context-retrieval-pipeline.md)
- [ADR 006: Replace Ollama SDK with Generic OpenAI-Compatible REST Provider](./planning/adr/006-openai-compatible-provider.md)
