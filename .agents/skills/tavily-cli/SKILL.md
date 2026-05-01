---
name: tavily
description: Tavily MCP tools for web search, content extraction, site crawling, and site mapping. Use this skill when the Researcher agent needs to search the web, extract content from URLs, crawl documentation sites, or map site structure. Auth via `TAVILY_API_KEY` in the user-level MCP config.
---

# Tavily MCP Skill

> Web research via the Tavily MCP server (`io.github.tavily-ai/tavily-mcp`). Provides four tools: search, extract, map, and crawl. All return structured data directly — no JSON parsing needed.

## Prerequisites

- MCP server `io.github.tavily-ai/tavily-mcp` configured in VS Code (user-level or workspace-level `mcp.json`)
- `TAVILY_API_KEY` set via the MCP input prompt
- Agent `tools:` array includes `'io.github.tavily-ai/tavily-mcp/*'`

## Tool Reference

### 1. `tavily_search` — Web Search

Web search. Best for: current information, community discussions, general documentation, news.

**Parameters:**
| Parameter | Type | Default | Purpose |
|-----------|------|---------|---------|
| `query` | string | *required* | Search query |
| `search_depth` | `basic` \| `advanced` | `basic` | Search thoroughness |
| `max_results` | integer (1–20) | 5 | Number of results |
| `topic` | `general` \| `news` \| `finance` | `general` | Search domain |
| `include_domains` | string[] | — | Restrict to these domains |
| `exclude_domains` | string[] | — | Exclude these domains |
| `time_range` | `day` \| `week` \| `month` \| `year` | — | Recency filter |
| `include_answer` | boolean | false | Include AI-generated answer |

**Example:**
```
tavily_tavily_search: query="requests library session handling", search_depth="advanced", max_results=8, include_domains=["docs.python.org"]
```

---

### 2. `tavily_extract` — URL Content Extraction

Extract full content from one or more known URLs. Best for: pulling a specific docs page, GitHub issue, or blog post.

**Parameters:**
| Parameter | Type | Default | Purpose |
|-----------|------|---------|---------|
| `urls` | string[] | *required* | URLs to extract content from |
| `extract_depth` | `basic` \| `advanced` | `basic` | Extraction thoroughness |

**Example:**
```
tavily_tavily_extract: urls=["https://docs.python.org/3/library/json.html"], extract_depth="advanced"
```

---

### 3. `tavily_map` — Site Structure Mapping

Discover all URLs on a website without extracting content. Best for: understanding site structure before extracting specific pages.

**Parameters:**
| Parameter | Type | Default | Purpose |
|-----------|------|---------|---------|
| `url` | string | *required* | Starting URL |
| `max_depth` | integer (1–5) | 1 | Levels deep to discover |
| `max_breadth` | integer | 20 | Links per page |
| `limit` | integer | 50 | Max URLs to discover |
| `select_paths` | string[] | — | Include only URLs matching these regex patterns |
| `exclude_paths` | string[] | — | Exclude URLs matching these regex patterns |

**Example:**
```
tavily_tavily_map: url="https://docs.example.com/api", max_depth=2, select_paths=["/api/.*"]
```

---

### 4. `tavily_crawl` — Multi-Page Content Crawling

Crawl a website and extract content from multiple pages. Best for: bulk extraction across related documentation pages.

**Parameters:**
| Parameter | Type | Default | Purpose |
|-----------|------|---------|---------|
| `url` | string | *required* | Starting URL |
| `max_depth` | integer (1–5) | 1 | Levels deep to crawl |
| `max_breadth` | integer | 20 | Links per page |
| `limit` | integer | 50 | Total pages cap |
| `instructions` | string | — | Natural language guidance for crawling |
| `extract_depth` | `basic` \| `advanced` | — | Extraction thoroughness |
| `select_paths` | string[] | — | Include only URLs matching these regex patterns |

**Example:**
```
tavily_tavily_crawl: url="https://docs.example.com/authorization", max_depth=2, limit=15, extract_depth="advanced"
```
