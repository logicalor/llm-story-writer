---
date: "2026-05-02"
issue: 302
pr: 314
category: agent
targets:
  - ".opencode/agents/coder.md"
severity: minor
status: archived
---

## Coder invoked ruff as `python -m ruff` instead of the standalone executable

### Finding

During issue #302 (PR #314, chunked outline generation), the Coder attempted to run ruff as
`.venv/bin/python -m ruff`, which failed. The ruff executable is installed at `.venv/bin/ruff` and
is invoked directly as `ruff check --fix <path>` / `ruff format <path>`. Ruff does not expose a
`__main__.py` entry point in this project's virtualenv, so `python -m ruff` produces a
`No module named ruff` error rather than a lint run.

### Observation

Rule 8 in `coder.md` already documents scope-limited ruff commands (`ruff format path/to/file.py`)
and Rule 1 references the copilot-instructions.md lint command (`ruff check --fix .`). Neither rule
explicitly stated that `ruff` is a standalone executable — not a Python module — and must not be
called via `python -m`. The gap is narrow but caused a failed lint invocation in a clean dispatch
that otherwise required no iteration.

The pre-existing `mypy src/` error (`src/tools/_io.py: Source file found twice`) was correctly
identified as out-of-scope and excluded. It is already documented in gotcha #044 (issue #298,
PR #310); no new improvement needed for that finding.

### Suggested Improvement

Add a one-line note to Rule 8's Scope-limited commands sub-bullet in `coder.md` clarifying the
direct invocation form:

> "Invoke ruff directly (`ruff check --fix path/to/file.py`, `ruff format path/to/file.py`) — do
> NOT use `python -m ruff`. Ruff is a standalone executable, not a Python module entry point."

### Action Taken

Applied: added direct-invocation note to Rule 8 Scope-limited commands sub-bullet in
`.opencode/agents/coder.md`.
