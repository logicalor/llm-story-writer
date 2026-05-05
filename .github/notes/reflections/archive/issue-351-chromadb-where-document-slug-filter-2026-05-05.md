---
date: "2026-05-05"
issue: 351
pr: 366
category: instruction
targets:
  - ".github/notes/gotchas.md"
severity: minor
---

## ChromaDB `where` only supports exact scalar equality — use `where_document=$contains` for slug filtering

### Finding

During PR #366 (feat/recap-chromadb-index), the Researcher surfaced that ChromaDB's `where`
clause only supports exact scalar equality matches (`{"field": "value"}`). It does NOT support
substring, prefix, list-contains, or partial-match queries on metadata fields. For index modules
that need to filter by participant slug or location slug (values that may appear among a list of
slugs), the `where` clause cannot be used reliably — the slugs must be prepended to the document
body, and filtering done via `where_document={"$contains": slug}`.

### Observation

This is a non-obvious gotcha for anyone implementing new ChromaDB index modules (e.g.
`recap_index.py`, `wiki_search.py`, future `chapter_index.py`). The ChromaDB documentation does
not prominently warn against this; developers naturally reach for `where={"participant": "alice"}`
expecting substring or partial-match semantics. The silent failure mode is that a metadata `where`
query with a slug stored as part of a comma-separated string or list simply returns zero results —
with no error, no warning, and no indication that the filter was incorrectly structured.

The established pattern (prepend slugs to document body, then query via
`where_document={"$contains": slug}`) is intentional in `recap_index.py` and `wiki_search.py`,
but without a written gotcha, future implementors will rediscover this independently.

### Suggested Improvement

Add gotcha #058 to `.github/notes/gotchas.md` documenting that ChromaDB `where` is exact scalar
equality only, and that slug filtering must use `where_document={"$contains": slug}` with the
slug prepended to the document body at index time.

### Action Taken

Applied: added gotcha #058 to `.github/notes/gotchas.md`.
