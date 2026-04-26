---
name: reflection
description: Use when capturing, collating, applying, or proposing improvements to this repository's agent system, Codex skills, workflow instructions, and durable reflection notes.
---

# Reflection

This is the Codex-native counterpart to `.github/agents/reflection.agent.md`. Use it to turn real workflow friction into durable improvements for agents, skills, instructions, and project notes.

## Scope

Reflection targets include:

- `.agents/skills/*/SKILL.md`
- `.agents/skills/*/references/*`
- `.github/agents/*.agent.md`
- `.github/agents/_shared/*`
- `.github/instructions/*`
- `.github/notes/*`
- `AGENTS.md`

Reflection notes live in `.github/notes/reflections/`. The `reflections` ChromaDB collection is a derived semantic index.

Use the current workspace as the source of truth for reflection availability. If this skill file exists locally, it is available for the session even when the file is new on the branch or absent from `origin/development`.

## When To Reflect

Reflect during a task when you discover:

- a workflow gotcha, contradiction, or missing instruction
- stale agent, skill, or documentation guidance
- a repeat mistake that should become a durable check
- unclear tool mapping, handoff, verification, or memory behavior

Reflect near the end of GitHub workflow tasks by checking active notes in `.github/notes/reflections/` and deciding whether any safe improvements should be applied or proposed.

## Workflow

1. Load `project-memory` when available and query the `reflections` collection for related prior issues.
2. Read `.github/notes/reflections/README.md` and `.github/notes/reflections/TEMPLATE.md` before creating or collating notes.
3. Record a note for each distinct observation using the canonical template. Prefer `issue-N-short-slug.md` when an issue number exists; use `general-short-slug.md` otherwise.
4. Classify each improvement:
   - `minor`: typos, clarifications, missing examples, broken links, formatting, or narrow instruction corrections.
   - `major`: new workflow steps, structural changes, new skills or agents, tool changes, policy changes, or anything with unclear blast radius.
5. Apply minor improvements precisely and record the exact action in the note.
6. Propose major improvements with target paths, rationale, expected impact, and the intended edit. Wait for user approval unless the current user request already explicitly asks for that change.
7. Add ChromaDB entries after the note exists when `mcp__chroma__` is available. If Chroma is unavailable, keep the file note as the source of truth.
8. Archive processed notes by moving them to `.github/notes/reflections/archive/` with a date suffix. Do not delete archived notes. Remove the active copy only after the archive copy exists.

## Chroma Guidance

Use `mcp__chroma__.chroma_query_documents` to find related prior reflections before acting.

Use `mcp__chroma__.chroma_add_documents` for new reflection entries. Include metadata with at least:

- `source_file`
- `date`
- `issue` when known
- `pr` when known
- `category`
- `target`
- `severity`
- `status`

## Constraints

- Do not use reflection as a dumping ground for transient logs or ordinary task notes.
- Do not silently change workflow behavior. Summarize any applied minor improvement.
- Preserve the style and structure of the target file.
- Make one targeted improvement per edit when possible.
- If unsure whether an edit is safe, treat it as major and propose it.
