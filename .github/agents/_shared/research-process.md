# Shared Research Process

> Common methodology for all researcher sub-agents. **Read this file first** before starting any research task.

## Tools

### Tavily MCP — Web Search, Extraction, Crawling, and Mapping

You have access to the Tavily MCP tools (`io.github.tavily-ai/tavily-mcp/*`) for all web research operations. All tools return structured data directly — no JSON parsing needed.

#### `tavily_search` — Web search

Best for: current information, community discussions, blog posts, general documentation, release notes.

```
tavily_search: query="query", search_depth="advanced", max_results=10
tavily_search: query="query", search_depth="advanced", include_domains=["docs.python.org", "github.com"]
```

#### `tavily_extract` — URL content extraction

Best for: pulling full content from a known URL (docs page, GitHub issue, blog post, RFC).

```
tavily_extract: urls=["https://example.com/page"], extract_depth="advanced"
tavily_extract: urls=["URL1", "URL2", "URL3"]
```

#### `tavily_map` — Site structure mapping

Best for: understanding the structure of a documentation site before extracting specific pages.

```
tavily_map: url="https://docs.example.com", max_depth=2
tavily_map: url="https://docs.example.com", select_paths=["/docs/latest.*"]
```

#### `tavily_crawl` — Multi-page content crawling

Best for: extracting content across multiple related pages in one pass.

```
tavily_crawl: url="https://docs.example.com/latest", max_depth=2, limit=20
tavily_crawl: url="https://example.com", instructions="Find all pages about authorization"
```

### Context7 — Library Documentation

You have access to `io.github.upstash/context7/*` which provides two tools:

#### `resolve-library-id` — Find library identifiers

Always call this first to get the Context7-compatible library ID.

```
libraryName: e.g. "python", "react", "fastapi", "django"
```

#### `get-library-docs` — Retrieve documentation

Call with the resolved ID and a specific topic.

```
context7CompatibleLibraryID: the ID from resolve-library-id
topic: specific topic to look up (e.g. "validation", "composables", "middleware")
```

### When to Use Which Tool

| Need | Tool |
| --- | --- |
| General question, current info, opinions | `tavily_search` |
| Known URL to read | `tavily_extract` |
| Explore a docs site structure | `tavily_map` |
| Bulk-read related pages | `tavily_crawl` |
| API reference, code examples, version-specific docs | Context7 `get-library-docs` |

---

## Research Process

### Step 1 — Understand the Brief

Before searching, restate what you are researching and why. Identify:

- The core question(s) to answer
- Any constraints (e.g. specific library version, framework requirements)
- What format the output should take (summary, comparison, code examples, etc.)

Check `.github/notes/` and query ChromaDB for any prior research on this topic — avoid redundant searches.

### Step 2 — Gather Information

> **Read `.github/skills/tavily-cli/SKILL.md` before performing web research** — it defines all available tools and their parameters.

Use the tools above to collect information from multiple sources. Best practices:

1. **Start broad, then narrow** — use `tavily_search` first to find relevant sources, then `tavily_extract` to read the most promising ones in detail.
2. **Use Context7 for API specifics** — when you need accurate function signatures, configuration options, or code patterns for a specific library.
3. **Cross-reference** — don't rely on a single source. Check at least 2–3 sources for key claims.
4. **Note version sensitivity** — always record which version of a library your findings apply to.
5. **Prefer official sources** — official documentation, MDN, GitHub repos over blogs or Stack Overflow for authoritative claims.

### Step 3 — Synthesise

After gathering raw information:

1. **Deduplicate** — multiple sources may say the same thing; use the most authoritative
2. **Evaluate** — note if sources conflict; flag uncertainty
3. **Contextualise** — relate findings to the project's technology stack (see `copilot-instructions.md`) when relevant
4. **Code examples** — prefer examples using the project's conventions when applicable

### Step 4 — Produce the Report

Structure the output consistently:

```markdown
## Research Report: [Topic]

**Date:** YYYY-MM-DD
**Brief:** [What was asked]
**Sources:** [number of sources consulted]

---

### Summary

[2–3 sentences: the key finding in plain language]

### Findings

#### [Sub-topic 1]

[Detail, with code examples if relevant]

#### [Sub-topic 2]

[Detail]

### Recommendations

[Specific, actionable conclusions]

### Gaps / Uncertainties

[Anything that couldn't be confirmed, or where sources conflict]

### Sources

- [URL or library name] — [brief description of what was found]
```

---

## Constraints

1. **Never write production code, tests, or configuration files** — only return a research report
2. **Never make implementation decisions** — report facts and options; let the calling agent or user decide
3. **Always cite sources** — every claim should be traceable to a URL or library reference
4. **Flag version sensitivity** — note when information is specific to a version that may differ from the project's stack
5. **Prefer official sources** — prioritise official documentation over community content for authoritative claims
