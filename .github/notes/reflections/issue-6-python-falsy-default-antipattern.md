---
date: "2026-04-13"
issue: 6
pr: 35
category: instruction
targets:
  - ".github/notes/gotchas.md"
severity: minor
status: archived
---

## Python `args.X or default` anti-pattern masks falsy-zero values

### Finding

During issue #6 (Build character-mgr Tool), the Coder wrote `args.budget or 500` to set a default word budget. This is a Python anti-pattern when argparse already provides `default=500`: the `or` fallback is redundant and silently converts valid falsy values (`0`, `""`) to the default. When a user explicitly passes `--budget 0`, they get 500 instead.

The Synthesized Review caught this as M-W-03 (majority confidence) — "Budget falsy-zero bug."

### Observation

This is a common Python gotcha, not specific to this project's architecture. It should be recorded for the future `conventions` collection under the `gotcha` category. The `conventions` collection doesn't exist yet (pending issue #7 reflection approval), so this is recorded here for embedding when it's created.

The general rule: never use `value or default` for argparse/CLI arguments. Argparse handles defaults; use `value` directly. If a secondary default is genuinely needed (e.g., for optional config overrides), use `value if value is not None else default`.

### Suggested Improvement

Record as a gotcha entry in `.github/notes/gotchas.md` when that file is created (per issue #7 reflection proposal):

```markdown
### G-XXX: Never use `args.X or default` for argparse arguments

`args.budget or 500` silently converts `--budget 0` to 500. Argparse already handles defaults — use `args.budget` directly. If a secondary default is needed, use `args.budget if args.budget is not None else 500`.
```

### Action Taken

Recorded. Will be embedded into `conventions` collection when `gotchas.md` is created per issue #7 proposal.
