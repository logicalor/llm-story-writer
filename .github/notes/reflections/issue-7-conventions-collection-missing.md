---
date: "2026-04-13"
issue: 7
pr: 34
category: instruction
targets:
  - ".github/instructions/chromadb.instructions.md"
  - ".github/agents/coder.agent.md"
severity: major
status: active
---

## ChromaDB `conventions` collection referenced but does not exist

### Finding

During issue #7 planning, the Orchestrator queried the `conventions` ChromaDB collection for relevant gotchas and patterns. The collection does not exist — only `tests`, `reflections`, and `codebase` are present. The Coder agent explicitly references this collection in its "Conventions & Gotchas" section: "query the ChromaDB `conventions` collection for gotchas relevant to the task domain."

The `chromadb.instructions.md` file lists `conventions` as a collection with a full metadata schema, sourced from `gotchas.md`, `patterns.md`, `architecture.md`, and `domain.md`. Of these source files, only `architecture.md` exists in `.github/notes/`. The other three (`gotchas.md`, `patterns.md`, `domain.md`) have never been created.

### Observation

This creates a silent failure: agents attempt to query a collection that doesn't exist, get no results or an error, and continue without the context they were supposed to have. The `conventions` collection was designed to provide gotchas, patterns, and architectural context for planning and implementation — its absence means agents are flying blind on accumulated project knowledge.

Two options:
1. **Create the collection and seed files.** Create `gotchas.md`, `patterns.md`, `domain.md` in `.github/notes/` with content extracted from existing reflections and architecture notes, then embed into a new `conventions` collection.
2. **Remove references until content exists.** Strip the `conventions` references from `chromadb.instructions.md` and `coder.agent.md`, and add it back when source content is ready.

Option 1 is preferred — there's enough accumulated knowledge from 7 issues of reflections to seed meaningful gotchas and patterns.

### Suggested Improvement

1. Create `.github/notes/gotchas.md` with entries extracted from reflection archive (security patterns from issue #3, stale doc patterns from issues #4/#5/#30, role boundary from issue #8).
2. Create `.github/notes/patterns.md` with tool implementation patterns (TypeScript wrapper → Python script, execFileSync, is_relative_to, etc.).
3. Create the `conventions` ChromaDB collection and embed the seed documents.
4. Verify the Coder agent's `conventions` query works end-to-end.

### Action Taken

Proposed for approval — this creates new knowledge base files and a new ChromaDB collection.
