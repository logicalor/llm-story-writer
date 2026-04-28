# OpenRouter Provider Mapping

Confirmed OpenRouter model slugs and corresponding Opencode model identifiers for the three models used across the 24 migrated agents.

## Model ID Reference

| Copilot display name | OpenRouter slug | Opencode model ID |
|---|---|---|
| `MoonshotAI: Kimi K2.6 (openrouter)` | `moonshotai/kimi-k2.6` | `openrouter/moonshotai/kimi-k2.6` |
| `Qwen: Qwen3.6 Plus (openrouter)` | `qwen/qwen3.6-plus` | `openrouter/qwen/qwen3.6-plus` |
| `Z.ai: GLM 5.1 (openrouter)` | `z-ai/glm-5.1` | `openrouter/z-ai/glm-5.1` |

## Authentication

OpenRouter is a first-class provider in Opencode. Authentication uses `OPENROUTER_API_KEY` from the environment or credentials stored via the `/connect` command.

Do **not** set `baseURL` in `opencode.json` for the `openrouter` provider — it is resolved natively by Opencode.

## Verification

Slugs confirmed against [openrouter.ai/models](https://openrouter.ai/models) on 2026-04-29.

To verify each model resolves without error, run:

```bash
OPENROUTER_API_KEY=<your-key> opencode run "hello" --model openrouter/moonshotai/kimi-k2.6
OPENROUTER_API_KEY=<your-key> opencode run "hello" --model openrouter/qwen/qwen3.6-plus
OPENROUTER_API_KEY=<your-key> opencode run "hello" --model openrouter/z-ai/glm-5.1
```

> **Note:** `OPENROUTER_API_KEY` was not available in the CI/development environment at implementation time. Each developer must verify locally after setting their key.

## Usage in Agent Frontmatter

When writing agent `.md` files in `.opencode/agents/`, reference models using the `model:` frontmatter field:

```yaml
---
model: openrouter/moonshotai/kimi-k2.6
---
```