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

## Coder Used `ruff format --check` (Dry Run) Instead of `ruff format` (Apply)

### Finding

During PR #337 (issue #325 — chroma-sync upsert/read-refresh), the Coder ran `ruff format --check` as part of its final cleanup step. The `--check` flag is a read-only dry run — it reports which files have formatting violations but does not apply any changes. Two files were left unformatted. The Documenter, dispatched later, ran `ruff format` (without `--check`) to apply the fixes.

### Observation

Rule 8's "Scope-limited commands" sub-bullet instructs coders to use `ruff format path/to/file.py` and `ruff check --fix path/to/file.py`, and explicitly names the applying forms. However, it does not contrast these against the read-only `--check` variants or explicitly state that `--check` does not fix anything. An agent unfamiliar with ruff's flag semantics may treat `--check` as the "correct" final-verification form and not notice that no changes were applied.

### Suggested Improvement

Append a sentence to the "Scope-limited commands" sub-bullet in Rule 8 of all three coder agent files:

> Always run the applying forms: `ruff format path/to/file.py` applies formatting; `ruff format --check` is read-only and reports violations without fixing them. Using `--check` during cleanup leaves formatting issues in place.

### Action Taken

Applied: appended the dry-run clarification to the "Scope-limited commands" sub-bullet in Rule 8 of:
- `.opencode/agents/coder.md`
- `.github/agents-copilot/coder.agent.md`
- `.github/agents-openrouter/coder.agent.md`
