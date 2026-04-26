# Tool Mapping

Copilot instructions in `.github/agents/` use tool names that are not Codex tool names. Translate them before acting.

## GitHub

Preferred in this environment:

- GitHub plugin/app tools exposed as `mcp__codex_apps__github.*` when available.
- `gh` CLI for operations not exposed by the connector, especially comments, branch/PR operations, workflow logs, and review thread details.
- Local `git` for branch, commit, merge, and push operations.

Do not assume Copilot names such as `github/issue_read`, `github/issue_write`, or `github/create_branch` exist in Codex.

## ChromaDB

Use `mcp__chroma__`:

- `chroma_query_documents`
- `chroma_get_documents`
- `chroma_add_documents`
- `chroma_update_documents`
- `chroma_get_collection_count`

## Web Research

Use `mcp__tavily__`:

- `tavily_search`
- `tavily_extract`
- `tavily_crawl`

Use `mcp__context7__` for library docs after resolving a library ID when that resolver is available. If only `get_library_docs` is exposed and no exact ID is known, use official docs via web search instead.

## Files

Use `rg` and `rg --files` for search. Use `apply_patch` for manual edits.

## Verification Commands

Project defaults:

```bash
ruff check --fix .
ruff format .
mypy src/
pytest
```

Prefer focused commands for narrow changes, but run broader checks when shared behavior changes.
