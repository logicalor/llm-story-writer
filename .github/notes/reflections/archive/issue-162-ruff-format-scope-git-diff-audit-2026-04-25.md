---
date: "2026-04-25"
issue: 162
pr: 172
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## Ruff format scope discipline: `git diff --name-only` audit before commit

### Finding

During the PR #172 review fix cycle, `ruff format .` (run repo-wide) silently reformatted
`tests/unit/test_openai_async_provider.py`, removing an unused `Mock` import. This file was
entirely out of scope for the task. The change had to be reverted manually with
`git checkout -- tests/unit/test_openai_async_provider.py` before committing.

This is the sixth occurrence of ruff scope inflation across the project's history (prior
occurrences: issues #5, #16, #21, #25, #90).

### Observation

Coder Rule 8 already mandates scope-limited commands ("use `ruff format path/to/file.py`
rather than `ruff format .`"). Despite this, the pattern recurs because the rule does not
describe an **audit step** that would catch scope inflation before a commit is made.

The practical gap: even when the intent is to run a scoped command, a developer may
inadvertently run `ruff format .` through habit or copy-paste. A `git diff --name-only`
inspection before staging provides a final scope gate that does not require remembering the
rule at command input time.

### Suggested Improvement

Add a **Pre-commit scope audit** sub-bullet to Coder Rule 8 in `.github/agents/coder.agent.md`:

> **Pre-commit scope audit:** Before committing, run `git diff --name-only` (or
> `git diff --cached --name-only` after staging) to confirm the changed file list matches your
> task scope. If `ruff format .` ran and touched out-of-scope files, revert them with
> `git checkout -- path/to/out-of-scope-file` before committing.

### Action Taken

Applied: added "Pre-commit scope audit" sub-bullet to Coder Rule 8 in
`.github/agents/coder.agent.md` with source attribution to issue #162, PR #172.
