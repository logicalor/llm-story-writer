---
date: "2026-05-03"
issue: 322
pr: 334
category: instruction
targets:
  - ".github/copilot-instructions.md"
severity: minor
---

## CI paths filter must include scripts invoked by the workflow step

### Finding

The CI workflow created in PR #334 (`.github/workflows/ci.yml`) runs
`python scripts/lint_no_inline_markdown.py` but its `on: pull_request: paths:` filter does
not include `scripts/lint_no_inline_markdown.py`. If the lint script itself is modified
(e.g. adding a new violation detector, changing the allowlist), the workflow will not
trigger on that change, silently leaving the gate un-exercised against the updated logic.

The `paths:` filter covers `stories/**`, `src/**/*_writer.py`, `src/**/*_manager.py`,
and `src/tools/**` — all appropriate — but omits the `scripts/` directory.

### Observation

The existing CI YAML Security bullet in `copilot-instructions.md` states:

> "Gate conditions for selective tests must include all high-risk file types — lock files,
> config files, etc. — not only the primary language file filter."

"Scripts invoked by the workflow step" is implicitly high-risk but is not listed alongside
lock files and config files. Without a concrete mention, agents creating CI workflows tend
to enumerate source file patterns and omit the invoker itself.

This is the same category of gap that the instruction was written to prevent — a silently
incomplete trigger condition — but the instruction's example list does not make the pattern
obvious for script-invocation cases.

### Suggested Improvement

Extend the bullet in the CI YAML Security section of `copilot-instructions.md` to explicitly
call out workflow-invoked scripts as a required path entry:

```diff
- **Gate conditions for selective tests must include all high-risk file types** — lock files, config files, etc. — not only the primary language file filter.
+ **Gate conditions for selective tests must include all high-risk file types** — lock files, config files, and any `scripts/` files invoked by the workflow step — not only the primary language file filter.
```

### Action Taken

Applied: extended the Gate conditions bullet in `.github/copilot-instructions.md` to include
`scripts/` files invoked by the workflow step.
