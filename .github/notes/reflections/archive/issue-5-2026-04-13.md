---
date: "2026-04-13"
issue: 5
pr: 29
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## Coder misses stale paths in documentation during file relocations

### Finding

During issue #5 (Prompt Template Relocation), 131 prompt templates were moved from `src/application/strategies/outline_chapter/prompts/` to top-level `prompts/`. The Coder correctly updated all source code path references but missed stale paths in two documentation/markdown files: `RECAP_SANITIZER_IMPROVEMENTS.md` and `src/application/strategies/README.md` (lines 118/124). The Synthesized Review caught these as majority/singular findings.

Additionally, ruff auto-formatting was applied alongside functional changes in the same commit, inflating the diff and making review harder. The unanimous review finding recommended separating formatting commits from functional commits.

### Observation

This is a recurring pattern. Issue #4 reflection noted ambiguous path documentation propagating errors; issue #5 shows the Coder not grepping broadly enough for old paths after a relocation. Coder Rule 6 currently says "run a grep for the original term across all **changed files**" — but the stale references were in files the Coder hadn't changed. The rule should instruct grepping the **entire workspace** for the original path/term when performing file relocations or renames.

The formatting-commits issue is a process gap — no agent instruction currently addresses when to commit auto-formatter changes separately.

### Suggested Improvement

1. **Coder Rule 6** — change "across all changed files" to "across the entire workspace" for relocations/renames, and add explicit mention of documentation/markdown files.
2. **Coder Rules** — add a new Rule 8 instructing the Coder to commit auto-formatter-only changes separately when ruff modifies files outside the task scope.

### Action Taken

Applied: Strengthened Coder Rule 6 to grep entire workspace (not just changed files) and explicitly mention docs/markdown. Added Rule 8 for separating formatting-only commits.
