---
date: "2026-04-21"
issue: 111
pr: 112
category: instruction
targets:
  - ".github/notes/gotchas.md"
severity: minor
status: archived
---

## Stale sibling file when savepoint format changes between .json and .md

### Finding

During PR #112, `save_savepoint` was updated to write `.md` for string values and `.json` for
structured values. When the type of a savepoint changes (e.g. from a dict to a string), the
old extension file persists on disk. `load_savepoint` has a priority rule: `.json` always
takes precedence over `.md`. If a string savepoint is written as `step.md` but an old
`step.json` still exists, `load_savepoint` returns the stale JSON data, silently ignoring the
fresh Markdown file.

### Observation

This is a stale-sibling problem: two files representing the same logical key but with different
extensions. The priority rule that makes reading deterministic also makes it a silent failure
vector when the two files coexist with different content.

The fix is to delete the sibling extension in `save_savepoint` before writing the new file:
when saving as `.md`, delete `<step>.json` if it exists; when saving as `.json`, delete
`<step>.md` if it exists. This keeps the sibling invariant clean at write time rather than
depending on the caller to clean up.

### Suggested Improvement

Add gotcha #009 to `.github/notes/gotchas.md`.

### Action Taken

Applied: added gotcha #009 to `.github/notes/gotchas.md`.
Embedded this reflection into the `reflections` ChromaDB collection.
