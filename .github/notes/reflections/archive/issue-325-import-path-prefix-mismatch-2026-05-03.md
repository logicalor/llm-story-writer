---
date: "2026-05-03"
issue: 325
pr: 337
category: agent
targets:
  - ".opencode/agents/coder.md"
  - ".github/agents-copilot/coder.agent.md"
  - ".github/agents-openrouter/coder.agent.md"
severity: minor
---

## Import Path Prefix Mismatch Causes mypy "Source File Found Twice" Error

### Finding

During PR #337 (issue #325 — chroma-sync upsert/read-refresh), the Coder added `from src.tools._chroma_sync import refresh_if_stale` to `wiki_snapshot.py`. All sibling tools in `src/tools/` use `from tools._chroma_sync import ...` (without the `src.` prefix). The mismatched prefix caused a mypy "Source file found twice under different module names" error. The Orchestrator had to fix it manually by replacing the prefix to match the file's existing convention.

### Observation

The existing inline-import sub-bullet (Rule 7) addresses *placement* (module-level vs inline). It does not address *path prefix* convention (`tools.X` vs `src.tools.X`). Both forms resolve at runtime, so ruff and pytest do not catch the mismatch — only mypy does, and only when both forms appear in the same mypy run. This is a distinct, unguarded failure mode.

### Suggested Improvement

Add a sub-bullet after the inline-import bullet in Rule 7 of all three coder agent files:

> **When adding a new import to a file** — match the import path prefix convention already present. If existing imports use `from tools.X import`, use the same; if they use `from src.tools.X import`, match that. Mismatched prefixes cause mypy "Source file found twice under different module names" errors. Read the first few existing imports to determine the file's convention before writing new ones.

### Action Taken

Applied: added the import path prefix sub-bullet to Rule 7 in:
- `.opencode/agents/coder.md`
- `.github/agents-copilot/coder.agent.md`
- `.github/agents-openrouter/coder.agent.md`
