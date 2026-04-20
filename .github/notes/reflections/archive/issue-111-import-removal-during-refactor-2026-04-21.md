---
date: "2026-04-21"
issue: 111
pr: 112
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## Coder removes existing imports when adding new module usage

### Finding

During PR #112, the Coder added usage of `_config.py` to `_llm.py` and in doing so removed
`import json` — which `_llm.py` still used elsewhere in the file. The missing import caused a
`NameError` at runtime. The issue was caught during manual review.

### Observation

When the Coder restructures imports (adding a new utility module, replacing inline logic with a
shared helper), it may mentally associate the old import with the logic it is replacing. If the
old import also serves other callsites in the same file, removing it silently breaks those paths.

This differs from stale-import detection (unused imports flagged by ruff/mypy). Here the import
*was* still needed — ruff's `F401 unused-import` rule would not catch it because the import
was used elsewhere. The breakage is a runtime `NameError`, not a lint error.

Coder Rule 7's dead-code sweep targets "unused functions, unreachable branches, abandoned
helpers" — not import statements. The gap is specific: when adding a new import (for a new
utility or refactored path), the Coder must verify that any imports it removes are genuinely
no longer needed by any code path in the file.

### Suggested Improvement

Add a sub-bullet to Coder Rule 7 in `.github/agents/coder.agent.md`:

> When adding a new `import` statement or refactoring to use a shared module — verify that any
> import you remove is not still used elsewhere in the same file. A removed import that was
> serving another callsite produces a runtime `NameError` that linters do not catch (the import
> was in use; it just no longer appears in the code path you modified).

### Action Taken

Applied: added sub-bullet to Coder Rule 7 about import removal during refactors.
Embedded this reflection into the `reflections` ChromaDB collection.
