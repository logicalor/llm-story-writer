---
date: "2026-05-03"
issue: 317
pr: 329
category: instruction
targets:
  - "docs/tools.md"
severity: minor
status: active
---

## `docs/tools.md` not updated to list `src/tools/_persist.py`

### Finding

PR #329 (issue #317) added `src/tools/_persist.py` as a new shared internal helper module
exposing `persist_markdown` and `read_markdown_ref`. The `docs/tools.md` "Shared Internal
Helpers" section — which lists `_io.py`, `_llm.py`, `_wiki.py`, and `migrate_state_slim.py` —
was not updated to include `_persist.py`.

### Observation

`docs/tools.md` is the canonical reference for the tool layer. Agents, contributors, and reviewers
consult it to understand what modules exist and what they provide. A missing entry means:

- Future Coders implementing persist helpers won't discover the module via documentation and may
  duplicate its functionality or import it incorrectly
- Reviewers checking whether new code should use `_persist.py` have no reference to find it
- The storage convention in `docs/planning/separate-markdown-from-json/convention.md` references
  the API but `docs/tools.md` is the expected authoritative inventory

### Suggested Improvement

Add a row to the "Shared Internal Helpers" table in `docs/tools.md`:

```markdown
| `src/tools/_persist.py` | Markdown pointer helpers: `persist_markdown` writes markdown to disk and returns a `{"$ref": ...}` pointer; `read_markdown_ref` resolves pointers or passthrough legacy strings |
```

This should be added after the `_io.py` row (alphabetical order within the shared helpers section).

### Action Taken

Applied: added `_persist.py` row to the Shared Internal Helpers table in `docs/tools.md`
(Reflection collation for issue #318, 2026-05-03).
