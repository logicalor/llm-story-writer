---
date: "2026-04-30"
issue: 252
pr: 253
category: instruction
targets:
  - ".github/notes/gotchas.md"
severity: minor
status: archived
---

## Opencode permission format (object-map, not array) absent from knowledge base

### Finding

Before PR #253, all 24 `.opencode/agents/*.md` files used an undocumented array-format permission schema (e.g., `permission.bash` as a list of allowed patterns, `permission.task` as a list of display names). The correct format — defined in Opencode's documented schema — uses an object-map with `"*": "deny"` as the default and pattern-specific `"allow"` overrides. The correct format was also noted: `permission.task` values must be agent file IDs (the filename without `.md`), not display names. And `tools:` entries use boolean `true`, not string `"allow"`. PR #253 corrected all 24 files.

### Observation

The `gotchas.md` knowledge base is the primary source for the ChromaDB `conventions` collection, which agents query before starting implementation. The correct Opencode permission format is now documented in `docs/features/opencode-runtime.md`, but that file is in the `codebase` ChromaDB collection, not `conventions`. A future Coder creating or editing `.opencode/agents/*.md` files performing a standard pre-task conventions query would not find the format specification, and could repeat the array-format mistake. Adding a gotcha entry makes the format discoverable via standard ChromaDB recall.

### Suggested Improvement

Add gotcha #038 to `.github/notes/gotchas.md` documenting the object-map permission format, the `"*": "deny"` default pattern, the agent file ID requirement for `task:` values, and the boolean `true` requirement for `tools:` entries. Embed in ChromaDB `conventions` collection.

### Action Taken

Applied: Added gotcha #038 to `.github/notes/gotchas.md` and embedded in ChromaDB `conventions` collection.
