---
name: documentation-maintenance
description: Use when updating docs, README content, ADRs, planning docs, or durable project notes after implementation or architecture changes.
---

# Documentation Maintenance

Update existing docs before creating new ones. Documentation must describe implemented behavior, not intended behavior.

## Workflow

1. Load `project-memory`.
2. Read the issue, PR, diff, or implementation files that define the actual behavior.
3. Find existing docs with `rg`.
4. Update docs and indexes together.
5. Verify paths, links, commands, examples, and behavior claims against the repo. Scan the full file for every occurrence of changed terms; don't assume a single-section edit is sufficient.
6. When files are renamed or ADR numbers change, verify all internal markdown links still resolve.
7. Run relevant markdown and code validation where available.
7. Add `.github/notes/` entries for gotchas or architectural learnings that should be remembered.

## Companion Sweeps

For architecture changes, ADRs, layer renames, tool changes, or workflow changes, sweep:

- `AGENTS.md`
- `.github/copilot-instructions.md`
- `docs/manual.md`
- `docs/tools.md`
- `.github/notes/architecture.md`
- `.github/notes/gotchas.md`
- `.agents/skills/`
- `.github/agents/` if the Copilot system remains in use

## Rules

- No placeholder sections.
- No broken markdown links.
- No stale `.opencode` or TypeScript wrapper claims unless explicitly historical.
- Tables must match body prose.
- README updates are required for user-visible CLI, workflow, or setup changes.
- Scan every occurrence of changed terms across the full document, not just the sections being edited.
