---
date: "2026-04-23"
issue: 154
pr: 155
category: instruction
targets:
  - ".github/notes/gotchas.md"
severity: minor
status: active
---

## Savepoint storage: `str` saves as `.md`, non-`str` saves as `.json`

### Finding

`FilesystemSavepointRepository.save_savepoint` branches on `isinstance(data, str)`: a `str`
argument is written verbatim as `{step}.md`; any other Python object is JSON-serialised and
written as `{step}.json`. `cmd_expand_to_scenes` was calling
`_save_savepoint(repo, step, json.dumps(scenes, indent=2))` (passing a string), which caused the
scene list to be stored as a `.md` file. The downstream `cmd_parse_definitions` in
`scene_writer.py` loaded the savepoint expecting a Python list (`.json` round-trip) and received
a raw JSON string instead, causing a type error at runtime.

### Observation

The type-dispatch behaviour is non-obvious — callers assume `json.dumps()` is the correct
serialisation step, when in fact the repository handles serialisation internally. The bug is
invisible to lint and type checks because both input types are valid Python. Test suites that
assert only on content (`assert saved == items`) do not catch the regression; only a type
assertion (`assert isinstance(saved, list)`) will.

### Suggested Improvement

Add gotcha 012 to `.github/notes/gotchas.md` documenting:
- The `str` → `.md` / non-`str` → `.json` branching rule
- The anti-pattern of pre-serialising with `json.dumps()` before passing to `_save_savepoint`
- The test corollary: assert the type of the loaded value, not only the content

### Action Taken

Applied: added gotcha 012 to `.github/notes/gotchas.md` under the Savepoints section.
