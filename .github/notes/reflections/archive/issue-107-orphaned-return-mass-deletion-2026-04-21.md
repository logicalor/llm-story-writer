---
date: "2026-04-18"
issue: 107
pr: 108
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## Orphaned control-flow statements survive mass method deletion

### Finding

During PR #108 (remove all legacy code and orphaned root-level artifacts, 275 files changed, 42k
deletions), the Coder removed multiple legacy shim methods from `rag_integration_service.py` but
left a bare `return` statement on line 504. The surrounding method context had been deleted; the
`return` was syntactically valid Python (appearing inside another method) but semantically dead —
a fragment of removed code. The Orchestrator caught and removed the orphaned statement before
committing.

### Observation

Rule 7 mandates a dead-code sweep — "unused functions, unreachable branches, abandoned helpers"
— but does not explicitly call out orphaned control-flow statements (`return`, `raise`,
`pass`, `continue`, `break`) left behind when the enclosing block is deleted.

This class of artifact is specifically easy to miss in mass-deletion diffs:

- The statement is syntactically valid and not flagged by ruff or mypy (a bare `return None`
  inside a method is not an error).
- The surrounding method structure may still be logically consistent — the orphaned statement
  doesn't produce import errors or type mismatches.
- Large diffs (42k deletions) are visually hard to audit line-by-line; orphaned fragments hide in
  the noise between blocks that were correctly deleted.

This is the first instance of this specific artifact class. Rule 7 already covers the conceptually
adjacent cases (dead functions, unreachable branches, stale comments) — adding one explicit sub-
bullet closes the coverage gap without structural change.

### Suggested Improvement

Add a sub-bullet to Coder Rule 7 in `.github/agents/coder.agent.md`:

> After removing multiple methods from a class in a mass deletion pass — scan the resulting file
> for orphaned control-flow statements (`return`, `raise`, `pass`) that have lost their enclosing
> context. A bare `return` or `raise` inside another method is syntactically valid Python but may
> be semantically dead. These are not flagged by ruff or mypy unless they cause type errors; they
> hide easily in large diffs.

### Action Taken

Applied: added Rule 7 sub-bullet about orphaned control-flow statements after mass method
deletion to `.github/agents/coder.agent.md`. Embedded this reflection into the `reflections`
ChromaDB collection.
