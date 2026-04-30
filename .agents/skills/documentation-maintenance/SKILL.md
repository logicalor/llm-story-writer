---
name: documentation-maintenance
description: Use when updating docs, README content, ADRs, planning docs, or durable project notes after implementation or architecture changes.
---

# Documentation Maintenance

Update existing docs before creating new ones. Documentation must describe implemented behavior, not intended behavior.

## Workflow

1. **Trivial-change short-circuit.** If the PR changes only agent instructions, skill files, config files, or documentation itself (no `.py` or `.ts` code), skip to output — no separate `docs/` update is needed. The changed files are self-documenting.
2. Load `project-memory`.
3. Read the issue, PR, diff, or implementation files that define the actual behavior.
4. Find existing docs with `rg`.
5. Update docs and indexes together.
6. Verify paths, links, commands, examples, and behavior claims against the repo. The depth of verification depends on PR type:
   - **Code-heavy PRs** (new features, API changes): verify routes, signatures, DB schemas, tool outputs against actual source.
   - **Config/agent/docs-only PRs** (no code changes): verify file paths, links, and prose consistency only. Skip code-specific checks.
7. When files are renamed or ADR numbers change, verify all internal markdown links still resolve.
8. Run relevant markdown and code validation where available.
9. Add `.github/notes/` entries for gotchas or architectural learnings that should be remembered.
10. **ChromaDB embedding:** If `mcp__chroma__` is available, embed updated docs. If unavailable, skip silently — do not retry.

## Companion Sweeps

For architecture changes, ADRs, layer renames, tool changes, or workflow changes, sweep all of the following — do not stop at the first match:

- `AGENTS.md`
- `.github/copilot-instructions.md`
- `docs/manual.md`
- `docs/tools.md`
- `.github/notes/architecture.md`
- `.github/notes/gotchas.md`
- `.agents/skills/`
- `.github/agents/` if the Copilot system remains in use

**Maximum files modified per dispatch: 5.** If the sweep identifies more than 5 files needing updates, apply the 5 most critical and defer the rest.

## Rules

- No placeholder sections.
- No broken markdown links.
- No stale `.opencode` or TypeScript wrapper claims unless explicitly historical.
- Tables must match body prose.
- README updates are required for user-visible CLI, workflow, or setup changes.
- Scan every occurrence of changed terms across the full document, not just the sections being edited.
