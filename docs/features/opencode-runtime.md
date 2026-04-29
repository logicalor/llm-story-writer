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

## Installation

Install Opencode globally before using the migrated agent runtime:

```bash
npm install -g opencode-ai
```

Then confirm the CLI is available:

```bash
opencode --version
```

If your environment uses a different Node.js package manager policy, install the same `opencode-ai` package through that tool and keep the `opencode` CLI on your `PATH`.

## Directory Layout

The repository keeps Opencode runtime files under `.opencode/`:

```text
.opencode/
├── agents/                # Active Opencode agent runtime definitions
│   ├── orchestrator-v3.md
│   ├── browser.md
│   ├── coder.md
│   ├── documenter.md
│   ├── reflection.md
│   ├── test-writer.md
│   ├── reviewer-kimi.md
│   ├── reviewer-qwen.md
│   ├── reviewer-glm.md
│   ├── synthesizing-reviewer.md
│   ├── pr-reviewer.md
│   ├── researcher.md
│   ├── researcher-kimi.md
│   ├── researcher-qwen.md
│   ├── researcher-glm.md
│   ├── synthesizing-researcher.md
│   ├── auditor.md
│   ├── auditor-kimi.md
│   ├── auditor-qwen.md
│   ├── auditor-glm.md
│   ├── synthesizing-auditor.md
│   ├── planner.md
│   ├── contemplator.md
│   └── sprint-runner.md
└── rules/                 # Plugin-loaded scoped instruction files
    └── chromadb.md
```

`agents/` contains the active Opencode runtime agent definitions. `rules/` contains plugin-loaded scoped instruction files applied by `opencode-rules`.

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

## opencode-rules Plugin

The project-level `opencode.json` includes `opencode-rules@latest` in its `plugin` array. That plugin reads Markdown files from `.opencode/rules/` and applies them as scoped instructions during Opencode runs.

This repository currently ships one scoped rule file: `.opencode/rules/chromadb.md`. Its frontmatter declares `globs: ["src/**/*.py"]`, which reproduces the `applyTo` scoping previously carried by `.github/instructions/chromadb.instructions.md`. The rule file also includes an inline comment that it must stay in sync with the shared instructions source.

## Migrated Agent Inventory

The Opencode runtime migration is now complete. `.opencode/agents/` contains exactly 24 Markdown agent files: the full migrated inventory from `.github/agents-openrouter/`, excluding that directory's README.

| Family | Files |
|---|---|
| Orchestrator | `orchestrator-v3.md` |
| Specialist sub-agents | `browser.md`, `coder.md`, `documenter.md`, `reflection.md`, `test-writer.md` |
| Reviewer family | `reviewer-kimi.md`, `reviewer-qwen.md`, `reviewer-glm.md`, `synthesizing-reviewer.md`, `pr-reviewer.md` |
| Researcher family | `researcher.md`, `researcher-kimi.md`, `researcher-qwen.md`, `researcher-glm.md`, `synthesizing-researcher.md` |
| Auditor family | `auditor.md`, `auditor-kimi.md`, `auditor-qwen.md`, `auditor-glm.md`, `synthesizing-auditor.md` |
| Standalone planning and dispatch agents | `planner.md`, `contemplator.md`, `sprint-runner.md` |

The three independent reviewer sub-agents remain intentionally triplicated because Opencode does not provide a native `extends` or `include` mechanism for shared agent bodies. Each file now carries an embedded sync notice at the top of its body stating that `reviewer-kimi.md`, `reviewer-qwen.md`, and `reviewer-glm.md` differ only in `model:` and `description:` frontmatter fields, and that any body-text change must be applied to all three files in lockstep.

Task 7 migrated the researcher family. Task 8 finished the remaining eight files: the auditor family plus `planner.md`, `contemplator.md`, and `sprint-runner.md`. With those files landed, the Opencode runtime now has full parity with the migrated OpenRouter agent set tracked in the Copilot-to-Opencode migration plan.

The researcher family still has the only developer-local MCP dependency in the agent inventory. `researcher.md`, `researcher-kimi.md`, `researcher-qwen.md`, `researcher-glm.md`, and `synthesizing-researcher.md` rely on Tavily and Context7 being present in `~/.config/opencode/opencode.json`; the repository root `opencode.json` still carries only the project-level Chroma configuration.

## Runtime Directories and Preserved Artefacts

The repository keeps three runtime-era agent directories during the migration transition period:

- `.opencode/agents/` is the active Opencode runtime. It contains 24 agent Markdown files with plain `.md` names and no `.agent.md` suffix.
- `.github/agents-copilot/` is preserved as the frozen Copilot artefact set. It also contains 24 agent files, but uses the `.agent.md` extension required by the Copilot surface.
- `.github/agents-openrouter/` is the intermediate OpenRouter migration set preserved from the migration path into Opencode.
- `.github/agents/` now contains only `_shared/` helpers for the Copilot surface rather than a full runtime inventory.

During the dual-run period, all three agent sets remain in the repository. None of these preserved directories were deleted.

## Dual-Run Policy

Both agent runtimes stay active during the migration transition period:

- GitHub Copilot agents run from `.github/agents-copilot/` through VS Code Chat `@agent-name` invocation.
- Opencode agents run from `.opencode/agents/` through `opencode run @agent-name`.

Any change to agent behaviour or instructions must be applied to both runtimes during this period. The project has not yet designated the long-term canonical source; that decision will happen separately. Until then, duplicated updates prevent Copilot and Opencode agents from drifting apart while migration work continues.

## Agent Migration Quick Reference

This table gives the per-file mapping between preserved Copilot agent definitions and their active Opencode counterparts.

| Agent Role | Copilot File (`.github/agents-copilot/`) | Opencode File (`.opencode/agents/`) |
|---|---|---|
| Orchestrator V3 | `orchestrator-v3.agent.md` | `orchestrator-v3.md` |
| Browser | `browser.agent.md` | `browser.md` |
| Coder | `coder.agent.md` | `coder.md` |
| Documenter | `documenter.agent.md` | `documenter.md` |
| Reflection | `reflection.agent.md` | `reflection.md` |
| Test Writer | `test-writer.agent.md` | `test-writer.md` |
| Reviewer (Claude → Kimi) | `reviewer-claude.agent.md` | `reviewer-kimi.md` |
| Reviewer (Gemini → Qwen) | `reviewer-gemini.agent.md` | `reviewer-qwen.md` |
| Reviewer (GPT → GLM) | `reviewer-gpt.agent.md` | `reviewer-glm.md` |
| Synthesizing Reviewer | `synthesizing-reviewer.agent.md` | `synthesizing-reviewer.md` |
| PR Reviewer | `pr-reviewer.agent.md` | `pr-reviewer.md` |
| Researcher | `researcher.agent.md` | `researcher.md` |
| Researcher (Claude → Kimi) | `researcher-claude.agent.md` | `researcher-kimi.md` |
| Researcher (Gemini → Qwen) | `researcher-gemini.agent.md` | `researcher-qwen.md` |
| Researcher (GPT → GLM) | `researcher-gpt.agent.md` | `researcher-glm.md` |
| Synthesizing Researcher | `synthesizing-researcher.agent.md` | `synthesizing-researcher.md` |
| Auditor | `auditor.agent.md` | `auditor.md` |
| Auditor (Claude → Kimi) | `auditor-claude.agent.md` | `auditor-kimi.md` |
| Auditor (Gemini → Qwen) | `auditor-gemini.agent.md` | `auditor-qwen.md` |
| Auditor (GPT → GLM) | `auditor-gpt.agent.md` | `auditor-glm.md` |
| Synthesizing Auditor | `synthesizing-auditor.agent.md` | `synthesizing-auditor.md` |
| Planner | `planner.agent.md` | `planner.md` |
| Contemplator | `contemplator.agent.md` | `contemplator.md` |
| Sprint Runner | `sprint-runner.agent.md` | `sprint-runner.md` |

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