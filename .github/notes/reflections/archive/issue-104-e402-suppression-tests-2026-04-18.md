---
date: "2026-04-18"
issue: 104
pr: 106
category: instruction
targets:
  - ".github/notes/gotchas.md"
severity: minor
status: archived
---

## E402 suppression in tests/: per-file-ignores is correct; root-level test_*.py intentionally excluded

### Finding

PR #106 added `[tool.ruff.lint.per-file-ignores]` to `pyproject.toml` suppressing Ruff E402 for
`tests/**/*.py`. The three-model synthesized review produced a 2–1 approval split. GPT held a
Warning that root-level `test_*.py` files (outside `tests/`) remain exposed to E402 and
interpreted this as an incomplete fix. Claude correctly identified the exclusion as intentional:
the root-level `test_*.py` files are legacy/ad-hoc scripts not registered in
`testpaths = ["tests/unit"]`, and the commit explicitly scoped to `tests/`. The Synthesizing
Reviewer downgraded GPT's Warning to Suggestion and approved merge.

### Observation

The E402 violations in `tests/` are a direct consequence of the `sys.path.insert` pattern
documented in gotcha #007 — `sys.path.insert` must appear before any `from src.*` import to
resolve package names, which places it before top-level imports and triggers Ruff rule E402
("module-level import not at top of file"). The per-file-ignore is the pragmatic, widely
accepted resolution.

Gotcha #007 documents `sys.path.insert` as an established convention, but does not mention
the E402 connection. A reviewer aware of #007 but not of the E402 link might still flag E402
violations as real defects rather than expected lint noise. Adding the E402 note to #007 closes
the loop between the convention and the lint rule it triggers.

The GPT false positive (root-level files as "incomplete fix") follows the recurring pattern of
GPT interpreting intentional scope limits as incompleteness. It was correctly handled by the
Synthesizing Reviewer architecture — no structural change required.

### Suggested Improvement

Update gotcha #007 in `.github/notes/gotchas.md` to add a paragraph explaining that the
`sys.path.insert` pattern is the root cause of E402 violations in test files, and that E402 is
suppressed for all files under `tests/` via `[tool.ruff.lint.per-file-ignores]` in
`pyproject.toml`. If E402 fires in a test file, verify the per-file-ignore is in place before
investigating import order.

### Action Taken

Applied: updated gotcha #007 in `.github/notes/gotchas.md` to add the E402 connection note.
Embedded this reflection into the `reflections` ChromaDB collection. Added gotcha #007 to the
`conventions` ChromaDB collection.
