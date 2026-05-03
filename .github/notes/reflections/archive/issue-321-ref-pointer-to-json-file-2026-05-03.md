---
date: "2026-05-03"
issue: 321
pr: 333
category: instruction
targets:
  - ".github/notes/gotchas.md"
severity: minor
---

## `$ref` pointer to a `.json` file — `read_markdown_ref` returns raw string; caller must use `json.loads()`

### Finding

PR #333 (issue #321, ADR 011 Task 6) introduced a `{"$ref": "outline/enrichment_suggestions.json"}`
pointer to a `.json` file. The ADR 011 pointer convention was designed primarily for markdown
content, but the same `{"$ref": "path"}` dict format is reused for structured JSON files
(e.g. `enrichment_suggestions.json`). The helper `read_markdown_ref` in `src/tools/_persist.py`
is named for markdown and works for JSON targets (it reads the file and returns its text), but
the caller receives a raw JSON **string**, not a parsed Python `dict`.

### Observation

A Coder implementing a read site for a JSON `$ref` pointer may call `read_markdown_ref` and then
immediately try to subscript the result (e.g. `result["character_enrichment"]`), silently
failing at runtime because `result` is a string, not a dict. There is no `read_json_ref`
companion helper to signal that parsing is required, and the naming `read_markdown_ref` does
not suggest JSON output.

There is also no convention for which path format (`read_markdown_ref` + `json.loads` vs.
direct `(story_root / ref["$ref"]).read_text()`) callers should use when the `$ref` target
is a `.json` file. Without documentation, callers vary independently.

### Suggested Improvement

Add gotcha #049 to `.github/notes/gotchas.md` under the "Savepoints / I/O" section,
documenting the JSON-target pointer pattern and the required `json.loads()` step.

### Action Taken

Applied: added gotcha #049 — `$ref` pointer to JSON files; `read_markdown_ref` returns raw
string; `json.loads()` required — to `.github/notes/gotchas.md`.
