---
date: "2026-04-25"
issue: 183
pr: 195
category: instruction
targets:
  - ".github/notes/gotchas.md"
  - "mypy.ini"
severity: major
status: active
---

## Dual module path conflict: src/tools/*.py seen under two names by mypy

### Finding

PR #195 (issue #183) added `update_wiki_from_chapter()` as a programmatic API to
`src/tools/wiki_extract.py`. Tool scripts in `src/tools/` use `from src.tools._io import ...`
style imports, requiring the project root on `sys.path`. When `src/presentation/agents/wiki_maintainer.py`
imports this API using `from tools.wiki_extract import update_wiki_from_chapter` (with `src/`
as the sys.path root), mypy sees the same physical file under two distinct module names:
`src.tools.wiki_extract` (via project root) and `tools.wiki_extract` (via src/ root) — and
raises a fatal type-checking error: `Source file found twice under different module names`.

The workaround applied in PR #195 was to add `[mypy-tools.wiki_extract] follow_imports = skip`
to `mypy.ini`. This suppresses mypy type-checking for the module entirely, sacrificing type
safety in exchange for unblocking the build.

Issue #196 was filed to track the long-term fix: extract programmatic APIs out of tool CLI
scripts into dedicated `src/tools/_*_api.py` helper files that use standard `src/`-relative
imports, eliminating the dual-path conflict.

### Observation

This is an architectural constraint of the hybrid import style in `src/tools/`. Every time a
programmatic API is extracted from a tool script and consumed by `src/presentation/` or
`src/application/` code, the same dual-module-path conflict will recur. The `follow_imports = skip`
workaround has two costs:

1. **Type coverage loss** — mypy does not check the module at all; type errors inside it
   silently go unreported.
2. **Precedent creep** — each new `follow_imports = skip` entry in `mypy.ini` widens the
   untyped surface and normalises suppression.

The correct structural fix is to separate the programmatic API surface from the CLI entry-point
surface: `src/tools/_wiki_api.py` (programmatic; uses standard `src/`-relative imports) vs.
`src/tools/wiki_extract.py` (CLI; uses project-root imports). The CLI entry point delegates to
the API module.

### Suggested Improvement

This is a **major** architectural change. Proposed for approval:

1. Add a gotcha entry to `.github/notes/gotchas.md` documenting the dual-module-path conflict
   pattern, the workaround, and the long-term fix.
2. Add a Coder Code Pattern noting that programmatic APIs extracted from `src/tools/` must be
   placed in `src/tools/_<name>_api.py` files using `src/`-relative imports — not added inline
   to the existing CLI script — to avoid the dual-path mypy conflict.
3. When implementing issue #196, remove the `[mypy-tools.wiki_extract] follow_imports = skip`
   override from `mypy.ini` and restore full type coverage.

### Action Taken

Proposed for approval — see Suggested Improvement above.
Gotcha entry and Coder rule pending approval before application.
