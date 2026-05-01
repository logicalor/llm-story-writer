# Task Breakdown: Migrate Copilot Skills to OpenCode Skills

> Implements [PRD](./prd.md)

**Date:** 2026-05-01

## Tasks

### Task 1: Port the three Copilot skills into `.agents/skills/`

**Type:** backend  
**Estimated scope:** small  
**Dependencies:** none

**Description:**

Create OpenCode-native copies of the three remaining Copilot skills by copying each directory from `.github/skills/{name}/` into `.agents/skills/{name}/` and applying the minimal adaptations listed below. The existing OpenCode functional skills (`project-memory`, `github-workflow`, `web-research`) must not be modified.

**Skill-specific adaptations:**

1. **chromadb-ops**
   - Copy `.github/skills/chromadb-ops/SKILL.md` → `.agents/skills/chromadb-ops/SKILL.md`
   - Update the script path inside `SKILL.md` from `bash .github/skills/chromadb-ops/scripts/chroma-embed.sh` to `bash .agents/skills/chromadb-ops/scripts/chroma-embed.sh`
   - Copy `.github/skills/chromadb-ops/scripts/chroma-embed.sh` → `.agents/skills/chromadb-ops/scripts/chroma-embed.sh`
   - Update the header comment in `chroma-embed.sh` that documents its own path
   - Keep the frontmatter `name` and `description` unchanged

2. **github-issues**
   - Copy `.github/skills/github-issues/SKILL.md` → `.agents/skills/github-issues/SKILL.md`
   - Copy `.github/skills/github-issues/references/tool-reference.md` → `.agents/skills/github-issues/references/tool-reference.md`
   - Replace all Copilot-style tool names with OpenCode tool names in both files:
     - `github/issue_read` → `github_issue_read`
     - `github/issue_write` → `github_issue_write`
     - `github/search_issues` → `github_search_issues`
     - `github/list_issues` → `github_list_issues`
     - `github/add_issue_comment` → `github_add_issue_comment`
   - Keep the frontmatter `name` as `github-issues`; update the `description` to mention Codex/OpenCode tools if desired, but this is optional

3. **tavily-cli**
   - Copy `.github/skills/tavily-cli/SKILL.md` → `.agents/skills/tavily-cli/SKILL.md`
   - Update tool invocation examples to use the exact OpenCode tool names:
     - `tavily_search:` → `tavily_tavily_search:`
     - `tavily_extract:` → `tavily_tavily_extract:`
     - `tavily_map:` → `tavily_tavily_map:`
     - `tavily_crawl:` → `tavily_tavily_crawl:`
   - Keep frontmatter `name` as `tavily` or change to `tavily-cli` for consistency with the directory name; either is acceptable as long as the skill is discoverable

**Acceptance Criteria:**

- [ ] `.agents/skills/chromadb-ops/SKILL.md` exists and its embedding-script path points to `.agents/skills/chromadb-ops/scripts/chroma-embed.sh`
- [ ] `.agents/skills/chromadb-ops/scripts/chroma-embed.sh` exists and its header comment reflects the new path
- [ ] `.agents/skills/github-issues/SKILL.md` exists and contains zero occurrences of `github/issue_` or `github/search_` or `github/list_` or `github/add_`
- [ ] `.agents/skills/github-issues/references/tool-reference.md` exists and also contains zero Copilot-style tool names
- [ ] `.agents/skills/tavily-cli/SKILL.md` exists and uses `tavily_tavily_*` tool names in all examples
- [ ] All three copied files render correctly as Markdown (no broken frontmatter, no orphaned relative links)

**Key Files:**

- `.agents/skills/chromadb-ops/SKILL.md` — new
- `.agents/skills/chromadb-ops/scripts/chroma-embed.sh` — new
- `.agents/skills/github-issues/SKILL.md` — new
- `.agents/skills/github-issues/references/tool-reference.md` — new
- `.agents/skills/tavily-cli/SKILL.md` — new

---

### Task 2: Sweep references and delete `.github/skills/`

**Type:** full-stack  
**Estimated scope:** small  
**Dependencies:** Task 1

**Description:**

Perform a mechanical global substitution of `.github/skills/` → `.agents/skills/` across all active agent, shared-process, and instruction files. Then delete the `.github/skills/` directory and verify no active file still references it.

**Files to update ( confirmed list from codebase grep ):**

1. `.opencode/agents/reflection.md` — line 110
2. `.opencode/agents/researcher.md` — line 58
3. `.opencode/agents/reflection.md.new` — line 110
4. `.opencode/agents/orchestrator-v3.md` — lines 84, 214, 400
5. `.opencode/agents/coder.md` — line 47
6. `.opencode/agents/documenter.md` — lines 32, 84, 128, 134
7. `.github/agents-copilot/coder.agent.md` — line 24
8. `.github/agents-copilot/orchestrator-v3.agent.md` — lines 163, 283, 311
9. `.github/agents-copilot/researcher.agent.md` — line 43
10. `.github/agents-copilot/reflection.agent.md` — lines 22, 80
11. `.github/agents-openrouter/orchestrator-v3.agent.md` — lines 163, 283, 311
12. `.github/agents-openrouter/coder.agent.md` — line 24
13. `.github/agents-openrouter/researcher.agent.md` — line 43
14. `.github/agents-openrouter/reflection.agent.md` — lines 22, 80
15. `.github/agents/_shared/code-review-process.md` — lines 35, 58, 61
16. `.github/agents/_shared/review-checklist.md` — line 122
17. `.github/agents/_shared/research-process.md` — line 94
18. `.github/instructions/chromadb.instructions.md` — lines 15, 41, 186, 243, 244

**Files to leave untouched (historical records):**

- `.github/notes/reviews/*.md`
- `.github/notes/reflections/archive/*.md`
- `.github/research/copilot-to-opencode-migration-2026-04-29.md`
- `docs/planning/copilot-to-opencode-migration/prd.md`
- `docs/planning/adr/009-opencode-as-primary-agent-runtime.md`

**Acceptance Criteria:**

- [ ] Every file in the "Files to update" list above has had `.github/skills/` replaced with `.agents/skills/`
- [ ] `grep -r '\.github/skills/' .opencode/agents/ .github/agents/ .github/instructions/` returns zero matches
- [ ] The `.github/skills/` directory has been deleted from the filesystem
- [ ] `git status` shows the deletions and edits; no unexpected files are modified

**Key Files:**

- All files listed in the "Files to update" section above

---

## Verification Script (post-Task-2)

Run the following commands to confirm the migration is complete:

```bash
# 1. New skills exist
ls .agents/skills/chromadb-ops/SKILL.md
ls .agents/skills/github-issues/SKILL.md
ls .agents/skills/tavily-cli/SKILL.md

# 2. Old directory is gone
! test -d .github/skills

# 3. No active references remain
grep -r '\.github/skills/' .opencode/agents/ .github/agents/ .github/instructions/ || echo "No active references found — OK"

# 4. Copilot-style tool names are gone from migrated skills
grep -r 'github/issue_' .agents/skills/github-issues/ || echo "No Copilot GitHub tool names found — OK"
```
