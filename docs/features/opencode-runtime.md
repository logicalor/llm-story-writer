# Opencode Runtime Configuration

> Project-level and user-level Opencode setup required for the OpenRouter-backed agent runtime introduced by migration Task 2.

## Overview

This repository now ships a project-level `opencode.json` that selects OpenRouter as the default Opencode provider surface for agent work. The checked-in file does two things only:

- sets the default model to `openrouter/moonshotai/kimi-k2.6`
- registers three named OpenRouter models under `provider.openrouter.models`

User-specific credentials and user-level MCP servers still stay outside the repository. Add those entries to `~/.config/opencode/opencode.json` and authenticate OpenRouter locally.

## Project-Level Configuration

The checked-in `opencode.json` contents in full:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "openrouter/moonshotai/kimi-k2.6",
  "instructions": ["AGENTS.md"],
  "plugin": ["opencode-rules@latest"],
  "provider": {
    "openrouter": {
      "models": {
        "moonshotai/kimi-k2.6": {
          "name": "MoonshotAI: Kimi K2.6"
        },
        "qwen/qwen3.6-plus": {
          "name": "Qwen: Qwen3.6 Plus"
        },
        "z-ai/glm-5.1": {
          "name": "Z.ai: GLM 5.1"
        }
      }
    }
  },
  "mcp": {
    "chroma": {
      "type": "local",
      "command": ["uvx", "chroma-mcp", "--client-type", "persistent", "--data-dir", ".chromadb"],
      "enabled": true
    }
  }
}
```

This file does not contain Tavily or Context7 entries. Those MCP servers remain developer-local by design.

## OpenRouter Authentication

Authenticate Opencode against OpenRouter in one of these supported ways:

1. Set `OPENROUTER_API_KEY` in your shell profile before launching Opencode.
2. Run `/connect` inside an Opencode session, choose `OpenRouter`, and paste your API key.

Opencode stores `/connect` credentials in `~/.local/share/opencode/auth.json`. The checked-in `opencode.json` does not hardcode `baseURL` or credentials; Opencode resolves the native `openrouter` provider itself.

## Confirmed Model IDs

Task 2 confirmed these OpenRouter model slugs and Opencode model identifiers:

| Display name | OpenRouter slug | Opencode model ID |
|---|---|---|
| `MoonshotAI: Kimi K2.6` | `moonshotai/kimi-k2.6` | `openrouter/moonshotai/kimi-k2.6` |
| `Qwen: Qwen3.6 Plus` | `qwen/qwen3.6-plus` | `openrouter/qwen/qwen3.6-plus` |
| `Z.ai: GLM 5.1` | `z-ai/glm-5.1` | `openrouter/z-ai/glm-5.1` |

The canonical mapping note lives in [../../.github/notes/opencode-provider-mapping.md](../../.github/notes/opencode-provider-mapping.md).

## Researcher Agent Family

Task 7 adds five migration-only Opencode agents under `.opencode/agents/` for web research and library documentation lookup:

| Agent file | Mode | Model | Dispatch policy | Tool scope |
|---|---|---|---|---|
| `researcher.md` | `primary` | `openrouter/moonshotai/kimi-k2.6` | `permission.task: deny` | Tavily, Context7, Chroma |
| `researcher-kimi.md` | `subagent` | `openrouter/moonshotai/kimi-k2.6` | `permission.task: deny` | Tavily, Context7 |
| `researcher-qwen.md` | `subagent` | `openrouter/qwen/qwen3.6-plus` | `permission.task: deny` | Tavily, Context7 |
| `researcher-glm.md` | `subagent` | `openrouter/z-ai/glm-5.1` | `permission.task: deny` | Tavily, Context7 |
| `synthesizing-researcher.md` | `primary` | `openrouter/moonshotai/kimi-k2.6` | `permission.task` allowlist: `Researcher Kimi`, `Researcher Qwen`, `Researcher Glm` | Tavily, Context7, Chroma |

The standalone `researcher.md` is the direct single-model entry point. The three model-specific files are sequential dispatch targets for `synthesizing-researcher.md`, which synthesizes their reports into one higher-confidence research result. All five files rely on developer-local Tavily and Context7 MCP servers being present in `~/.config/opencode/opencode.json`; the repository root `opencode.json` still carries only the project-level Chroma configuration.

## User-Level MCP Servers

### Tavily

Add Tavily only to your personal Opencode config. It is not committed to the repository.

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

### Context7

Add Context7 only to your personal Opencode config.

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

Both snippets belong in `~/.config/opencode/opencode.json`, not the repository root.

## Verification

Once `OPENROUTER_API_KEY` is available, verify model resolution locally:

```bash
opencode run "hello" --model openrouter/moonshotai/kimi-k2.6
opencode run "hello" --model openrouter/qwen/qwen3.6-plus
opencode run "hello" --model openrouter/z-ai/glm-5.1
```

If you rely on Tavily, verify that `TAVILY_API_KEY` is exported before starting Opencode.

## Related

- [Documentation Index](../README.md)
- [ADR 009: Opencode as Primary Agent Runtime](../planning/adr/009-opencode-as-primary-agent-runtime.md)
- [Migration Tasks](../planning/copilot-to-opencode-migration/tasks.md)