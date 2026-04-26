---
name: project-memory
description: Use when planning, implementing, reviewing, documenting, or reflecting in this repository and prior project knowledge may matter. Loads the Codex-native memory protocol for .github/notes and ChromaDB recall.
---

# Project Memory

Use this skill before substantive repository work. The authoritative memory store is `.github/notes/`; ChromaDB is a derived semantic index.

## Start Of Task

1. Read `.github/notes/README.md` for note conventions if the task may create or update knowledge.
2. Read topic files relevant to the task: commonly `architecture.md`, `gotchas.md`, `deferred.md`, and `repo.md`.
3. Query ChromaDB before planning, implementing, testing, reviewing, or documenting.
4. Treat Chroma hits as pointers. Verify important claims against files in the repo before acting.

## Chroma Queries

Use `mcp__chroma__` tools when available:

```text
conventions: gotchas, patterns, architecture notes
reflections: active agent-system improvement notes
audits: audit findings and health reports
codebase: feature docs, ADRs, skills, module facts
tests: test patterns and fixtures
```

For detailed schemas, ID conventions, and examples, read `references/chromadb.md`.

## Writing Memory

1. Write new durable knowledge to `.github/notes/` first.
2. Include `Date`, `Source`, and enough context for a future agent to trust the note.
3. Add or update the matching ChromaDB document after the note exists.
4. Do not store secrets, transient logs, or unverified guesses as durable memory.

## Scope

This skill is for project memory and recall only. Use task-specific skills for GitHub workflow, planning, testing, reviewing, documentation, or web research.
