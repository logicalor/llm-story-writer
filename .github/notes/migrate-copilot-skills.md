## Copilot-to-OpenCode Skill Migration Plan

**Date:** 2026-05-01
**Source:** Planner — skill migration planning

### Findings

The `.github/skills/` directory still contains three Copilot-specific skills that have no OpenCode equivalents in `.agents/skills/`:

| Copilot skill | Unique content | Proposed OpenCode location |
|---------------|---------------|---------------------------|
| `chromadb-ops` | Embedding script path, cwd warning for `.chromadb` | `.agents/skills/chromadb-ops/` (new) |
| `github-issues` | Detailed tool inventory, decision flowchart, common mistakes | `.agents/skills/github-issues/` (new) |
| `tavily-cli` | Parameter tables for all 4 Tavily tools | `.agents/skills/tavily-cli/` (new) |

Existing OpenCode functional skills (`project-memory`, `github-workflow`, `web-research`) were intentionally kept untouched. Merging would increase scope; copying and minimally adapting is the shortest path.

### Tool-name mappings (Copilot → OpenCode)

| Copilot | OpenCode |
|---------|----------|
| `github/issue_read` | `github_issue_read` |
| `github/issue_write` | `github_issue_write` |
| `github/search_issues` | `github_search_issues` |
| `github/list_issues` | `github_list_issues` |
| `github/add_issue_comment` | `github_add_issue_comment` |
| `tavily_search` | `tavily_tavily_search` |
| `tavily_extract` | `tavily_tavily_extract` |
| `tavily_map` | `tavily_tavily_map` |
| `tavily_crawl` | `tavily_tavily_crawl` |

### Active files referencing `.github/skills/`

A grep sweep found 18 files across `.opencode/agents/`, `.github/agents-copilot/`, `.github/agents-openrouter/`, `.github/agents/_shared/`, and `.github/instructions/` that still contain `.github/skills/`. Historical archives in `.github/notes/reviews/` and `.github/notes/reflections/archive/` are intentionally excluded from the sweep.

### Decision

Keep migrated skills as separate directories in `.agents/skills/` rather than merging into existing functional skills. This preserves the existing OpenCode skill structure, avoids large rewrite tasks, and gives agents the choice to load granular reference skills only when needed.

### Plan location

- PRD: `docs/planning/migrate-copilot-skills-to-opencode/prd.md`
- Tasks: `docs/planning/migrate-copilot-skills-to-opencode/tasks.md`
