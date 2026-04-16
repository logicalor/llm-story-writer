# ADR 003: Replace PostgreSQL/pgvector with ChromaDB for Local RAG

**Date:** 2026-04-12
**Status:** Accepted

## Context

The current RAG system uses PostgreSQL with the pgvector extension, requiring Docker Compose to run a database server. This adds operational complexity to what is intended to be a single-user, local-first application. The migration to OpenCode provides an opportunity to simplify the storage layer.

Options considered:

1. **Keep PostgreSQL/pgvector** — proven, but requires Docker Compose, database migrations, credentials management
2. **ChromaDB** — lightweight, file-based, Python-native, already used in the agent system's knowledge base
3. **Pure file-based retrieval** — keyword search over Markdown files, no vector store at all
4. **SQLite + sqlite-vss** — single-file database with vector search

## Decision

Replace PostgreSQL/pgvector with **ChromaDB** for story content RAG.

Rationale:
- ChromaDB is already a project dependency (used for the `.chromadb/` agent knowledge base)
- It requires no server process — stores data in local files
- It supports the same embedding model (Ollama nomic-embed-text) already configured
- It provides semantic search capabilities that pure file-based retrieval lacks
- Per-story collections provide natural isolation

**Collection structure:**
- One ChromaDB collection per story: `story-{story-name}`
- Documents indexed: outline chunks, chapter content, character sheets, setting sheets, recaps
- Metadata: `content_type` (outline/chapter/character/setting/recap), `chapter_number`, `scene_number`

**Storage location:** `.chromadb/stories/{story-name}/` (separate from the agent system's `.chromadb/` root)

## Consequences

### Positive

- No Docker Compose required — application runs with just Ollama + OpenCode
- Consistent technology stack (ChromaDB used for both agent knowledge and story RAG)
- Simpler setup: `pip install chromadb` vs. PostgreSQL + pgvector + Docker
- Per-story isolation is natural (separate collection per story)

### Negative

- ChromaDB is less mature than PostgreSQL for production workloads (acceptable for single-user local use)
- Migration of existing stories from pgvector requires a one-time migration script
- ChromaDB's query API is different from pgvector's SQL-based queries — tool code must be rewritten
- No ACID transactions across collections (acceptable for single-user, sequential pipeline)

### Neutral

- Embedding model (nomic-embed-text via Ollama) is unchanged
- Content chunking logic (ContentChunker) is unchanged
- Query semantics (similarity search with threshold) are equivalent
