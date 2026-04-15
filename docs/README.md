# Documentation

> Index for llm-story-writer project documentation.

## Architecture

- [Architecture Notes](../.github/notes/architecture.md) — System architecture, layer structure, pipeline flow, prompt template categories

## Tools

- [Tools Reference](./tools.md) — Tool architecture pattern, prompt-loader, story-state, savepoint-mgr, character-mgr, setting-mgr, recap-manager, outline-generator, scene-writer, critique-runner, wiki-init, wiki-read, wiki-search, wiki-snapshot, wiki-update, and wiki-lint tools, guide for adding new tools

## Features

- [Story Orchestrator](./features/story-orchestrator.md) — Primary pipeline controller agent: 9-phase story generation lifecycle, quality gates, wiki lifecycle, savepoint strategy, subagent delegation
- [Wiki Maintainer](./features/wiki-maintainer.md) — Wiki maintenance subagent: entity extraction, confidence scoring, detail levels, alias identification, chapter boundary procedures

## Planning

- [PRD: OpenCode Migration](./planning/opencode-migration/prd.md) — Full product requirements for the agentic architecture migration
- [Migration Tasks](./planning/opencode-migration/tasks.md) — Task breakdown and completion status

### Architecture Decision Records

- [ADR 001: Hybrid Agent-Tool Architecture](./planning/adr/001-hybrid-agent-tool-architecture.md)
- [ADR 002: Context Window Budget Strategy](./planning/adr/002-context-window-budget-strategy.md)
- [ADR 003: ChromaDB Replaces pgvector](./planning/adr/003-chromadb-replaces-pgvector.md)
- [ADR 004: Progressive Wiki Memory System](./planning/adr/004-progressive-wiki-memory-system.md)
- [ADR 005: Hybrid Wiki Context Retrieval Pipeline](./planning/adr/005-hybrid-wiki-context-retrieval-pipeline.md)
