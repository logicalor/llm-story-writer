---
date: "2026-04-30"
issue: 257
pr: 259
category: agent
targets:
  - ".opencode/agents/documenter.md"
  - ".github/agents-copilot/documenter.agent.md"
severity: minor
status: archived
---

## Documenter omits parent agent when enumerating a family

### Finding

Issue #257 (PR #259) fixed `docs/features/opencode-runtime.md` line 197 to state that both the researcher and auditor families carry developer-local MCP dependencies. The Documenter correctly identified that the auditor family required updating but listed only the three model-specific sub-agents (`auditor-kimi.md`, `auditor-qwen.md`, `auditor-glm.md`). The parent agent `auditor.md` — which also carries Tavily and Context7 in its frontmatter — was omitted from the enumeration. The synthesized review caught this as a unanimous finding (U-W-01) and a second dispatch corrected it.

### Observation

The Documenter's verification checklist has a bullet for inventory tables requiring cross-check against `ls` output, and a bullet for file paths in prose requiring disk verification. Neither bullet explicitly addresses the case of enumerating all members of a named agent family (parent + sub-agents + synthesizer). When the task says "the auditor family carries X", the Documenter focused on the files it associated with "sub-agent variants" rather than running a directory query to enumerate all files belonging to that family by prefix. The parent agent is the canonical definition of the family and its absence from a file list is a meaningful omission.

This is the same root cause pattern as `issue-7-documenter-verification-gap` (Documenter wrote inaccurate file extensions and output formats because the verification checklist didn't cover those cases). The fix is the same: add an explicit checklist bullet for the uncovered case.

### Suggested Improvement

Add a verification bullet to the `### 3. Write Documentation` checklist in both documenter files, immediately after the inventory tables bullet:

> - For agent family enumerations in prose (e.g., "the researcher family comprises…", "the auditor family and its sub-agents…"): run `ls .opencode/agents/ | grep <family-prefix>` to enumerate all family members before writing the list. A named family includes the parent agent (e.g., `auditor.md`), all model-specific sub-agents (e.g., `auditor-kimi.md`, `auditor-qwen.md`, `auditor-glm.md`), and the synthesizing agent (e.g., `synthesizing-auditor.md`). Do not rely on memory — enumerate from disk. (Source: issue #257, PR #259 — initial doc fix listed only the three auditor sub-agent variants and omitted `auditor.md`.)

### Action Taken

Applied: added family enumeration verification bullet to `.opencode/agents/documenter.md` and `.github/agents-copilot/documenter.agent.md`, immediately after the inventory tables bullet.
