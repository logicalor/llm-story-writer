---
name: chromadb-ops
description: "ChromaDB vector index operations for the knowledge base. Use when embedding documents into ChromaDB collections, querying semantic search, or managing the .chromadb/ index."
---

## ChromaDB Operations

Manage the ChromaDB semantic vector index over the `.github/notes/` knowledge base.

### When to use

- Embedding new or updated documents from `.github/notes/` into ChromaDB collections
- Querying ChromaDB for relevant prior knowledge during planning
- Creating or managing ChromaDB collections

### Embedding Script

Run the embedding script to sync knowledge base changes into ChromaDB:

```bash
bash .agents/skills/chromadb-ops/scripts/chroma-embed.sh
```

### Collection Schema

See `.github/instructions/chromadb.instructions.md` for collection schemas, ID conventions, and metadata formats.

### Available Collections

| Collection | Content |
|---|---|
| `conventions` | Gotchas, patterns, architecture notes |
| `reflections` | Agent improvement notes |
| `audits` | Audit synthesis reports |
| `codebase` | Code structure facts |
| `tests` | Test patterns and conventions |

### CLI Invocation Requirement

`chroma-mcp` in `.github/mcp.json` uses `cwd: "."` with `--data-dir .chromadb`.

> **Always invoke Copilot CLI from the project root.** The `.chromadb` data directory
> path resolves relative to your working directory at invocation time. Running from any
> other directory will cause `chroma-mcp` to target the wrong (or missing) data directory
> — ChromaDB will appear empty or fail to persist documents silently.
