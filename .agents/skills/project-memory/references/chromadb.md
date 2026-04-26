# ChromaDB Reference

The repo uses ChromaDB as a derived semantic index over `.github/notes/` and selected docs. Markdown files are authoritative.

## Collections

| Collection | Purpose | Typical Query Time |
| --- | --- | --- |
| `conventions` | Gotchas, patterns, architecture, domain notes | planning, implementation, review |
| `reflections` | Agent-system improvement notes | reflection, workflow edits |
| `audits` | Audit reports and findings | planning, review, architecture work |
| `codebase` | Feature docs, ADRs, skills, modules | planning, documentation |
| `tests` | Test patterns, fixtures, failure learnings | test writing and review |

## Standard Queries

Before planning:

```json
{
  "collection_name": "conventions",
  "query_texts": ["<feature or fix description>"],
  "n_results": 10
}
```

Before implementation:

```json
{
  "collection_name": "conventions",
  "query_texts": ["<task description>"],
  "n_results": 10,
  "where": {
    "$or": [
      {"category": {"$eq": "gotcha"}},
      {"category": {"$eq": "pattern"}}
    ]
  }
}
```

Before tests:

```json
{
  "collection_name": "tests",
  "query_texts": ["<test domain>"],
  "n_results": 5
}
```

Before documentation:

```json
{
  "collection_name": "codebase",
  "query_texts": ["<feature name>"],
  "n_results": 5
}
```

## Write Pattern

1. Add or update the Markdown source in `.github/notes/`.
2. Use stable IDs.
3. Include `source_file` metadata.
4. Use `chroma_add_documents` for new IDs and `chroma_update_documents` for existing IDs.

Never delete from `conventions` or `reflections` as part of normal task work. Update or supersede instead.
