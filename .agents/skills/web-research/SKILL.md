---
name: web-research
description: Use when current external information, official documentation, web search, content extraction, or library/API research is needed for this repository.
---

# Web Research

Use web research when facts may have changed, the user asks to look something up, or external docs are needed.

## Source Preference

1. Official documentation and primary sources.
2. Release notes and source repositories.
3. Maintainer discussions or issues.
4. Secondary summaries only as leads, not authority.

## Tools

Use `mcp__tavily__` when available:

- `tavily_search` for broad discovery.
- `tavily_extract` for known URLs.
- `tavily_crawl` for related docs pages.

Use Context7 for library docs when an exact library ID is known or can be resolved by available tools. For OpenAI product/API questions, use official OpenAI docs only.

## Output

Summarize findings with source links. Distinguish source facts from inference. Do not paste long copyrighted text.
