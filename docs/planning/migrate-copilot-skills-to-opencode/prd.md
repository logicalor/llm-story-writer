# PRD: Migrate Copilot Skills to OpenCode Skills

> Move the three remaining GitHub Copilot skills from `.github/skills/` into `.agents/skills/` so OpenCode agents can load them, then delete the old directory and update all references.

**Date:** 2026-05-01
**Author:** Planner agent
**Status:** Draft

## Problem Statement

The project is migrating its primary agent runtime from GitHub Copilot to OpenCode (ADR 009). The `.agents/skills/` directory already hosts OpenCode-native skills such as `web-research`, `github-workflow`, and `project-memory`. However, three Copilot-specific skills remain in `.github/skills/` only:

- `chromadb-ops` — ChromaDB embedding script and cwd warnings
- `github-issues` — Detailed GitHub issue tool reference and decision flowchart
- `tavily-cli` — Tavily MCP parameter tables and examples

These skills are referenced by active agent files (`.opencode/agents/`, `.github/agents-openrouter/`, `.github/agents-copilot/`, `.github/agents/_shared/`) and by `.github/instructions/chromadb.instructions.md`. Until they live in `.agents/skills/`, OpenCode agents cannot discover them natively, and the codebase retains stale Copilot-only artefacts.

## Goals

1. Every skill that exists in `.github/skills/` also exists in `.agents/skills/` with content adapted for the OpenCode runtime.
2. All active agent, shared-process, and instruction files point to `.agents/skills/` instead of `.github/skills/`.
3. The `.github/skills/` directory is removed.

## Non-Goals

- **Merging into existing OpenCode skills.** The existing `.agents/skills/` functional skills (`project-memory`, `github-workflow`, `web-research`) remain untouched. Merging would increase implementation and review effort; keeping the migrated skills separate is the shortest path.
- **Updating historical archives.** Review synthesis files, archived reflection notes, and research reports that mention `.github/skills/` are historical records and are intentionally left unchanged.
- **Rewriting Copilot agent prompts.** Only the skill *path* references inside agent files change; no agent logic or model assignments are modified.

## User Stories

### As an OpenCode orchestrator agent
- I want to load `github-issues/SKILL.md` from `.agents/skills/` so that I can follow the correct GitHub issue tool patterns.
- I want to load `chromadb-ops/SKILL.md` from `.agents/skills/` so that I know how to invoke the embedding script and avoid the cwd trap.
- I want to load `tavily-cli/SKILL.md` from `.agents/skills/` so that I have detailed Tavily parameter tables at hand.

### As a repository maintainer
- I want to delete `.github/skills/` without breaking active agents, so the Copilot-to-OpenCode migration is mechanically complete for the skill layer.

## Proposed Solution

### Shortest-path approach

1. **Copy each skill directory** from `.github/skills/{name}/` to `.agents/skills/{name}/`.
2. **Adapt content** minimally for OpenCode:
   - `chromadb-ops`: update the script path and the cwd warning text.
   - `github-issues`: replace Copilot-style tool names (`github/issue_read`) with the OpenCode tool names (`github_issue_read`, etc.).
   - `tavily-cli`: update frontmatter and, where needed, tool invocation examples to use the exact OpenCode Tavily tool names (`tavily_tavily_search`, etc.).
3. **Global mechanical substitution**: replace every occurrence of `.github/skills/` with `.agents/skills/` in active configuration files (`.opencode/agents/`, `.github/agents-openrouter/`, `.github/agents-copilot/`, `.github/agents/_shared/`, `.github/instructions/`).
4. **Delete `.github/skills/`** and verify no remaining references in active files.

### Why not merge into existing skills?

The existing OpenCode functional skills (`project-memory`, `github-workflow`, `web-research`) provide high-level workflow guidance. The Copilot skills provide granular tool reference (parameter tables, flowcharts, common-mistake lists). Keeping them separate avoids a large rewrite-and-merge task, preserves the existing skill structure, and lets agents load the reference skill only when they need it.

## Acceptance Criteria

- [ ] `.agents/skills/chromadb-ops/SKILL.md` exists and references `.agents/skills/chromadb-ops/scripts/chroma-embed.sh`.
- [ ] `.agents/skills/github-issues/SKILL.md` exists and uses OpenCode tool names (`github_issue_read`, `github_issue_write`, `github_search_issues`, `github_list_issues`, `github_add_issue_comment`).
- [ ] `.agents/skills/tavily-cli/SKILL.md` exists with frontmatter updated for the OpenCode context.
- [ ] No active agent file (`.opencode/agents/`, `.github/agents-openrouter/`, `.github/agents-copilot/`), shared-process file (`.github/agents/_shared/`), or instruction file (`.github/instructions/`) contains the string `.github/skills/`.
- [ ] The `.github/skills/` directory no longer exists in the repository.

## Open Questions

- Should the `github-issues` skill also include a note about `gh` CLI as a fallback, given that `github-workflow` prefers `gh` for some operations?  
  *Resolution: out of scope for this migration; the skill can be refined later.*
- Do any `.opencode/agents/` files load skills by path that will break if the skill name changes?  
  *Resolution: skill names stay identical, only the base directory changes, so paths are safe.*

## Related

- ADR 009: Opencode as Primary Agent Runtime (`docs/planning/adr/009-opencode-as-primary-agent-runtime.md`)
- Research report: `copilot-to-opencode-migration-2026-04-29.md`
- `.github/notes/reflections/archive/issue-20-opencode-directory-convention-2026-04-15.md`
