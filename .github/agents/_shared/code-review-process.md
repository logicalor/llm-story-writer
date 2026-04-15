# Code Review Process — Shared Protocol

> Shared review checklist and output format for agents that perform local code reviews. This process reviews changes on the current branch against `development` using local git — no GitHub API calls.

---

## Prerequisites

Before reviewing:

1. **Obtain the diff** — run `git diff development...HEAD -- . ':!vendor'` to get all changes. **Do NOT use pre-existing diff artefact files** (`diff.txt`, `commits.txt`, `changed_files.txt`, or similar) that may exist in the working directory — these are stale artefacts from previous tasks and will cause you to review the wrong PR. Always run the `git diff` command to obtain the live diff.
2. **List changed files** — run `git diff --name-only development...HEAD` to identify scope
3. **Read each changed file** — use `read` to view the full file (not just the diff) for context
4. **Check commit messages** — run `git log --oneline development..HEAD` to review commit quality

### Pre-Computed Package Mode

When dispatched by the **Synthesizing Reviewer**, your prompt includes a **Review Package** (delimited by `== REVIEW PACKAGE ==` / `== END REVIEW PACKAGE ==`) containing the branch name, commit log, changed file list, full diff, and full file contents — all pre-collected by the synthesizer.

In this mode:

- **Skip Prerequisites 1–4** — the data is already in the package
- Use the package data for all review phases
- You may still run **targeted** commands for specific verification (e.g., checking if a file referenced in the code exists on disk, grepping for a specific pattern across the workspace) — but do not re-run the bulk data collection commands

This eliminates redundant I/O when multiple reviewer models are dispatched against the same branch.

---

## Review Phases

Work through each phase in order. Use `todo` to track progress.

### Phase 1 — Structural Review

Check the branch structure:

- [ ] **Commit messages** — clear, follow convention (`feat:`, `fix:`, `refactor:`, etc.), reference issue number
- [ ] **Branch name** — follows convention (`feat/issue-N-...` or `fix/issue-N-...`)
- [ ] **Scope** — reasonable size (if >500 lines changed, note as a concern)
- [ ] **No unrelated changes** — all changes relate to the stated purpose
- [ ] **Numbered step lists** — in any agent or skill file with numbered steps, verify no gaps in the sequence (1, 2, 3… N with no missing integers); gaps appear when a step is deleted without renumbering the rest
- [ ] **File relocation** — if any files were moved or renamed, grep the entire workspace for the old path (`grep -r 'old/path' . --include='*.md' --include='*.sh' --include='*.yaml' --include='*.yml'`); update all consumers (agents, skills, instructions, docs, test scripts, CI workflows, pre-commit hooks)
- [ ] **Sibling item orphaning** — if an entire docs section, table block, or directory group was removed, verify that any *remaining* items at the same level are still referenced and documented; run `ls` of the parent directory to confirm what still exists on disk
- [ ] **Stale prose counts** — after any removal that changes the size of a list, table, or group, grep for adjacent numeric counts ("N skills", "N tools", "N rows", "N models", "N variants", etc.) and update them
- [ ] **`tools:` array coupling** — check both directions when any `tools:` array entry changes: **(1) If removing:** grep all agent body text and shared process files (`_shared/*.md`) for references to that tool (`grep -rn 'tool-name' .github/agents/ .github/skills/`); body instructions must be updated in the same PR — a partial removal leaves the agent in a broken runtime state. **(2) If adding body text that references a new tool group** (e.g., "query ChromaDB", "call chroma/*"): verify that tool group is already declared in the `tools:` array of every agent and model-specific variant that will inherit or execute the instruction
- [ ] **Model-specific variant sync** — when any parent agent with model-specific variants is edited (`researcher.agent.md`, `reviewer.agent.md`, `auditor.agent.md`), verify the same change is applied to all three model-specific variants (`*-claude.agent.md`, `*-gemini.agent.md`, `*-gpt.agent.md`); variants must remain identical to the parent except for the `model:` field — tools array changes and body text changes must be mirrored exactly
- [ ] **Section heading drift** — when body text under a section heading is substantially changed or replaced with content serving a different purpose, verify the heading still accurately describes the new content; a stale heading (e.g., `## Repo Memory` after migrating from vscode/memory to ChromaDB) actively misleads agents and humans scanning the document
- [ ] **YAML frontmatter section removal** — if any named section is removed from a YAML frontmatter block (e.g., `handoffs:`, `hooks:`, `callbacks:`), grep all body text in the same file and in `_shared/*.md` for prose references to that section by label name (`grep -rn 'handoffs\|hooks\|callbacks' .github/agents/ .github/skills/`); body instructions that describe the removed section must be updated in the same PR
- [ ] **Agent `model:` field format** — if any `.agent.md` file is created or edited, verify its `model:` field is a single scalar string (not an array). The Copilot CLI does not support model fallback arrays. Valid examples: `Claude Opus 4.6 (copilot)`, `GPT-5.4 (copilot)`, `Gemini 3.1 Pro (Preview) (copilot)`. Array syntax (e.g. `model: [claude-3-5-sonnet, gpt-4o]`) silently fails at dispatch time.
- [ ] **Shell snippet safety** — when reviewing shell code embedded in agent or skill files (`.agent.md`, `SKILL.md`, `_shared/*.md`): **(1) Absolute paths** — `rm`, file writes, and path operations must use paths anchored to `$(git rev-parse --show-toplevel)` rather than bare relative filenames that depend on CWD (e.g. `rm -f diff.txt` silently succeeds even if the file is in the repo root and CWD is a subdirectory). **(2) Error guards** — commands whose output is used in subsequent steps must have a `|| exit 1` guard so failure does not silently produce an empty or invalid value.

### Phases 2–7 — Backend, Frontend, Security, Testing, Performance, Documentation

> Follow the shared review checklist in **`.github/agents/_shared/review-checklist.md`** for Phases 2–7. This file defines the complete checklists for Code, Security, Testing, Performance, and Documentation review.

---

## Finding Format

Use this format for each finding in the report:

```
[FINDING-ID] Title
Category: Security | Correctness | Performance | Style | Testing | Documentation
Severity: Critical | Warning | Suggestion
File: path/to/file.ext
Lines: N-M (or "N" for single line, or "general" for file-level)
Description: What was found — be specific and explain why it matters
Suggestion: How to fix it (code example if helpful)
```

### Severity Definitions

- **Critical** — Must be fixed before merge (security vulnerability, bug, breaking change, convention violation that affects correctness)
- **Warning** — Should be fixed (potential bug, performance issue, convention violation)
- **Suggestion** — Nice to have (style improvement, minor optimization, documentation)

### Category Definitions

- **Security** — Vulnerabilities, authorization issues, data exposure
- **Correctness** — Bugs, logic errors, incorrect behavior
- **Performance** — N+1 queries, missing indexes, inefficient code
- **Style** — Convention violations, formatting, naming
- **Testing** — Missing tests, incorrect assertions, test quality
- **Documentation** — Missing or incorrect documentation

---

## Output Format

Produce a structured **Code Review Report** with the following sections:

### Review Summary

2–3 sentences: overall assessment, scope of changes, most significant findings.

**Files Reviewed:** N
**Findings:** N Critical, N Warning, N Suggestion

### Findings

Group by severity, then by category:

#### Critical Findings

```
[C-01] Title
Category: ...
Severity: Critical
File: path/to/file.ext
Lines: N-M
Description: ...
Suggestion: ...
```

#### Warning Findings

Same format as Critical.

#### Suggestions

Same format as Critical.

### Overall Assessment

One paragraph summary: Is the code ready for merge? What are the key risks? Any patterns of concern?
