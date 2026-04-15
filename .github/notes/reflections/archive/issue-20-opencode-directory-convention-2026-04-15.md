---
date: "2026-04-15"
issue: 20
pr: 62
category: instruction
targets:
  - "AGENTS.md"
severity: minor
status: archived
---

## AGENTS.md missing `.opencode/agents/` and `.opencode/skills/` directory documentation

### Finding

Issue #20 created the first agent definition in `.opencode/agents/story-orchestrator.md` and the first skill in `.opencode/skills/story-pipeline/SKILL.md`. AGENTS.md documents `.opencode/tools/` (TypeScript wrappers) under the Architecture section but does not mention the `.opencode/agents/` or `.opencode/skills/` directories.

With Tasks 18–20 upcoming (outline-planner, chapter-writer, wiki-maintainer subagents), more files will be created in `.opencode/agents/`. The directory convention needs to be documented so future agents are created in the correct location.

### Observation

The project has two parallel directory structures:
- `.github/agents/` — development workflow agents (Orchestrator V3, Coder, Documenter, etc.) managed by GitHub Copilot
- `.opencode/agents/` — story generation runtime agents (story-orchestrator) managed by OpenCode

Similarly for skills:
- `.github/skills/` — development skills (chromadb-ops, github-issues, etc.)
- `.opencode/skills/` — story generation skills (story-pipeline)

This split is architecturally correct but undocumented, creating ambiguity for future agent/skill creation tasks.

### Suggested Improvement

Add `.opencode/agents/` and `.opencode/skills/` to the Architecture section of AGENTS.md alongside the existing `.opencode/tools/` entry.

### Action Taken

Applied: added Agents and Skills subsections to the Architecture section of AGENTS.md documenting the `.opencode/agents/` and `.opencode/skills/` directories.
