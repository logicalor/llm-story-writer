# Opencode Runtime Configuration

User-level setup required for full agentic capability in this project. These entries go in `~/.config/opencode/opencode.json` (or the platform equivalent) — **not** in the project-level `opencode.json`.

## MCP Servers

### Tavily (Web Search)

Provides web search capability to agents via the `tavily-mcp` server.

**Prerequisites:** A [Tavily API key](https://app.tavily.com/).

Add to `~/.config/opencode/opencode.json`:

```json
{
  "mcp": {
    "tavily": {
      "type": "local",
      "command": ["npx", "-y", "tavily-mcp@latest"],
      "env": {
        "TAVILY_API_KEY": "<your-tavily-api-key>"
      },
      "enabled": true
    }
  }
}
```

### Context7 (Library Documentation)

Provides up-to-date library documentation lookup via the `@upstash/context7-mcp` server.

Add to `~/.config/opencode/opencode.json`:

```json
{
  "mcp": {
    "context7": {
      "type": "local",
      "command": ["npx", "-y", "@upstash/context7-mcp@latest"],
      "enabled": true
    }
  }
}
```

## OpenRouter

Authentication for the OpenRouter provider (used for Kimi K2.6, Qwen3.6 Plus, and GLM 5.1) can be set via:

1. **Environment variable** — set `OPENROUTER_API_KEY` in your shell profile.
2. **TUI connect command** — run `/connect` inside an Opencode session, search for "OpenRouter", and paste your API key.

Your API key is stored at `~/.local/share/opencode/auth.json` after using `/connect`.

> This file is a stub. Task 10 of the Copilot-to-Opencode migration will expand it with full runtime validation instructions and dual-run configuration.