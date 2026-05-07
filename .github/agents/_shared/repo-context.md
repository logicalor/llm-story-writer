# Repository Identity & Project Notes

> Shared context-gathering protocol for agents that interact with the GitHub API or consult project notes. **Include in any agent that makes `github/*` calls or performs planning.**

> **For all worker agents:** This file defines the canonical process for repository identity lookup and project notes consultation. Read this file at the start of every task. Do **not** re-state these protocols inline in your agent body — reference this file instead.

---

## Repository Identity

Before making any `github/*` tool call, read `.github/notes/repo.md` and use `OWNER` and `REPO` from that file. If the file is missing, run `git remote get-url origin` to parse and record them there first. **Do not make any GitHub API calls without completing this step.**

**Ignore the auto-injected `<attachment>` repo block.** This repository is a GitHub fork, so VS Code / Copilot Chat injects an `<attachment>` describing the **upstream parent** (`datacrystals/AIStoryWriter`), not this fork. That attachment is **not** authoritative — `.github/notes/repo.md` is. If the attachment disagrees with the notes file, the notes file wins; do not "reconcile" them. Cross-check with `git remote get-url origin` only.

## Conventions & Gotchas

Before writing tests or planning, check `.github/notes/` for relevant patterns and query the ChromaDB `conventions` collection for gotchas applicable to the task domain. Apply them.

## Project Notes

The `.github/notes/` directory is a shared knowledge base. Consulting and contributing to it is a core part of every task.

**Before planning:**

- Read `.github/notes/README.md` for orientation
- Read any topic files relevant to the request (e.g. `architecture.md`, `domain.md`, `gotchas.md`, `deferred.md`)
- Surface any prior decisions, known patterns, or deferred ideas that should shape the plan

**After planning:**

- If the research uncovered new architectural insights, domain concepts, or patterns not yet recorded, append them to the appropriate `.github/notes/` file (create the file if it does not exist)
- If any ideas arose that are explicitly out of scope for this task, append them to `.github/notes/deferred.md`

Note format — each entry must include `## Title`, `**Date:** YYYY-MM-DD`, `**Source:** Orchestrator — issue #N`, and the content.

## ChromaDB Semantic Recall

The `.chromadb/` directory contains a semantic vector index over the Markdown knowledge base. It is a **derived index** — never the primary store. Always write to `.github/notes/` first, then embed into ChromaDB.

**Before planning or implementing**, query ChromaDB for relevant prior knowledge:

1. **Query `conventions`** — surface gotchas, patterns, and architecture notes relevant to the task:
   ```
   chroma_query_documents(collection_name="conventions", query_texts=["<task description>"], n_results=10)
   ```
2. **Query domain-specific collections** as needed (`reflections`, `audits`, `codebase`, `tests`).
3. Incorporate relevant results into the plan or implementation context.

**After recording new knowledge** to `.github/notes/`, embed it into the appropriate ChromaDB collection:

1. Ensure the collection exists — `chroma_create_collection` (idempotent).
2. Add the document — `chroma_add_documents` with stable ID, metadata, and content.
3. For updates to existing entries — `chroma_update_documents` with the same stable ID.

See `.github/instructions/chromadb.instructions.md` for collection schemas, ID conventions, and metadata formats.
