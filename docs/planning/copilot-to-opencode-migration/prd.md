# PRD: Migrate Agentic Framework from GitHub Copilot to Opencode

> Migrate the project's agent system — 24 agents, 3 skills, 1 instruction file, and 1 MCP server — from GitHub Copilot's `.github/` customization model to Opencode's `opencode.json` + `.opencode/` model, while preserving the existing Synthesized Review and multi-model research workflows. Source of truth: `.github/agents-openrouter/`. Provider: OpenRouter.

**Date:** 2026-04-29
**Author:** Planner agent
**Status:** Draft
**Related research:** [.github/research/copilot-to-opencode-migration-2026-04-29.md](../../../.github/research/copilot-to-opencode-migration-2026-04-29.md)

---

## Problem Statement

The project currently runs its agentic development workflow through GitHub Copilot Chat in VS Code. The active agent system lives in `.github/agents-openrouter/` (24 agents using OpenRouter-hosted models) and supporting customizations live in `.github/skills/`, `.github/instructions/`, and `.github/mcp.json` / `.vscode/mcp.json`. The team wants to evaluate Opencode (https://opencode.ai) as the primary agent runtime because Opencode is open-source, terminal-first, model-agnostic, and supports the same fundamental abstractions (agents, skills, MCP servers, project rules) without requiring VS Code or a proprietary IDE.

The OpenRouter-based agents use three models across the multi-model families: `MoonshotAI: Kimi K2.6` (primary / orchestration), `Qwen: Qwen3.6 Plus` (Qwen family reviewers/researchers/auditors), and `Z.ai: GLM 5.1` (GLM family reviewers/researchers/auditors). Opencode supports OpenRouter as a provider via its OpenAI-compatible endpoint; exact model IDs require confirmation during Task 2.

Migrating is non-trivial because:

1. Opencode and Copilot share concepts but use different file paths, frontmatter schemas, configuration formats, and tool-permission models.
2. Several agents share frontmatter conventions (`tools:`, `model:`, GitHub-prefixed tool names like `github/create_branch`) that have no direct Opencode equivalent and require translation, not just reformatting.
3. The orchestrator and synthesizer patterns rely on programmatic sub-agent dispatch, which Opencode supports through `permission.task` and the Task tool — a different mechanism from Copilot's `runSubagent`.
4. The `chromadb.instructions.md` file uses `applyTo` glob scoping, which Opencode does not natively support — a community plugin (`opencode-rules`) is needed.
5. The team must continue working in Copilot during the migration, so the Copilot artefacts must not be removed until Opencode is proven.

The research report identified all four mappings, the gaps, and a phased migration strategy. This PRD turns that research into a concrete delivery plan.

## Goals

1. Run the project end-to-end in Opencode TUI (or `opencode run`) using the same agent topology currently working under Copilot.
2. Migrate every agent file in `.github/agents-openrouter/` (24 files) to a working Opencode equivalent under `.opencode/agents/`.
3. Preserve the multi-model Synthesized Review and Synthesized Research workflows (Kimi/Qwen/GLM families), including the file-persisted dispatch pattern that resolved the depth-2 nesting issue (PR #70).
4. Keep `.agents/skills/` skills working without modification (they are already discovered natively by Opencode).
5. Migrate the project's committed MCP server (`chroma`) to `opencode.json`. The `tavily` and `context7` MCP servers are user-level and must be documented for user-level Opencode config, not committed to the project.
6. Preserve `applyTo`-style scoped instruction injection for the ChromaDB instruction file via the `opencode-rules` plugin.
7. Keep `.github/agents-openrouter/` and all other existing Copilot customizations intact during the migration so the team can dual-run.

## Non-Goals

- **Not migrating the runtime story-generation pipeline.** The Python orchestrator in `src/presentation/orchestrator.py`, the prompts in `prompts/agents/`, and the `story-pipeline` skill are out of scope. This migration only covers the agentic _development_ framework that supports day-to-day coding work.
- **Not deleting `.github/agents-openrouter/`, `.github/agents-copilot/`, `.github/skills/`, `.github/instructions/`, `.github/mcp.json`, or `.vscode/mcp.json`** as part of this migration. Decommissioning Copilot artefacts is a separate decision after the Opencode runtime is proven.
- **Not changing the `.agents/skills/` skill content.** Skills are already in a directory Opencode scans natively. Moving or rewriting them is unnecessary.
- **Not implementing `.prompt.md` equivalents.** The two `.github/prompts/*.prompt.md` entry-point files (`work-on-issue`, `work-on-task`) have no clean Opencode equivalent and are out of scope. They can be replaced by `@agent-name` invocations at the TUI prompt instead.
- **Not migrating `AGENTS.md`.** It already exists at the project root and is read by Opencode natively.
- **Not changing tool inventories or model assignments.** Each migrated agent uses the same model and the same conceptual capability surface as its OpenRouter original in `.github/agents-openrouter/`; only the schema changes.
- **Not committing `tavily` or `context7` MCP entries to `opencode.json`.** These are user-level servers. Migration guidance documents the required entries for each developer's `~/.config/opencode/opencode.json`.

## User Stories

### Project maintainer

- As a project maintainer, I want to run `opencode` in the project root and have all 24 development agents available so I can work without VS Code or Copilot Chat.
- As a project maintainer, I want the Synthesized Review workflow to continue working under Opencode (Reviewer × 3 + Synthesizing Reviewer) so I do not lose the multi-model consensus quality gate.
- As a project maintainer, I want ChromaDB MCP queries to work in Opencode so the Reflection agent and the Coder can recall conventions and gotchas.

### Agent system contributor

- As a contributor extending the agent system, I want Opencode and Copilot agent files to be in clearly separate directories so I can extend either runtime independently and tell them apart at a glance.
- As a contributor, I want the `opencode-rules` plugin to inject the ChromaDB instructions only when working on `src/**/*.py` files so context stays lean.

## Proposed Solution

### Directory layout after migration

```
opencode.json                              # NEW — root Opencode config
.opencode/
  agents/                                  # NEW — 24 migrated agent files
    orchestrator-v3.md
    coder.md
    test-writer.md
    documenter.md
    reflection.md
    contemplator.md
    sprint-runner.md
    auditor.md
    auditor-kimi.md
    auditor-qwen.md
    auditor-glm.md
    synthesizing-auditor.md
    researcher.md
    researcher-kimi.md
    researcher-qwen.md
    researcher-glm.md
    synthesizing-researcher.md
    reviewer-kimi.md
    reviewer-qwen.md
    reviewer-glm.md
    synthesizing-reviewer.md
    pr-reviewer.md
    planner.md
    browser.md
  rules/                                   # NEW — applyTo-equivalent
    chromadb.md
.agents/skills/                            # UNCHANGED — already discovered natively
.github/agents-openrouter/                 # UNCHANGED — source of truth for migration, kept for dual-run
.github/agents-copilot/                    # UNCHANGED — kept for Copilot VS Code users
.github/skills/                            # UNCHANGED — kept for dual-run
.github/instructions/                      # UNCHANGED — kept for dual-run
.github/mcp.json                           # UNCHANGED — kept for dual-run
.vscode/mcp.json                           # UNCHANGED — kept for dual-run
AGENTS.md                                  # UNCHANGED — read natively by Opencode
```

### Backend (Opencode runtime)

Single `opencode.json` at the project root, JSONC, with five sections:

- `$schema` — points to `https://opencode.ai/config.json`
- `model` — default model for primary interactions
- `instructions` — array including `AGENTS.md` and any always-on instruction files
- `plugin` — list including `opencode-rules@latest` for `applyTo`-equivalent scoping
- `mcp` — local server entry for `chroma` only (tavily and context7 are user-level)
- `agent` — agent-specific overrides for MCP tool scoping where needed

Agent files live as plain markdown in `.opencode/agents/<agent-name>.md` with the filename as the agent name. Frontmatter uses Opencode's schema (`description`, `mode`, `model`, `permission`, `tools`, `temperature`, `hidden`).

The shared rules referenced by Copilot agents (`.github/agents/_shared/*.md`) stay in place. They are loaded through `read_file` calls inside agent prompts exactly as they are today — Opencode reads markdown the same way Copilot does. No `_shared/` rewrites are required.

### Frontend (CLI / TUI)

There is no UI work. The Opencode TUI replaces the VS Code Copilot Chat sidebar. Agent dispatch happens through:

- TUI manual invocation: `@agent-name` mention
- Programmatic dispatch from primary agents: the built-in Task tool, governed by `permission.task` allowlists in the orchestrator's frontmatter

### Database

No schema changes. ChromaDB collections stay identical and are accessed through the same MCP server, just configured under `opencode.json` instead of `.mcp.json`.

### Multi-model dispatch architecture

The current "file-persisted dispatch" pattern (PR #70) is preserved unchanged:

1. The orchestrator (Opencode primary agent) dispatches each Reviewer / Researcher / Auditor sub-agent sequentially, depth 1.
2. Each sub-agent writes its raw report to `.github/notes/reviews/` or `.github/notes/research/`.
3. The Synthesizing agent reads those files (no further sub-agent dispatch) and writes the consensus report.

This pattern translates 1:1 to Opencode using `permission.task` for the orchestrator's dispatch allowlist. The synthesizer's `permission.task` should be set to deny everything so it cannot accidentally re-introduce nesting.

## Acceptance Criteria

- [ ] `opencode.json` exists at the project root, validates against `https://opencode.ai/config.json`, and includes the chroma MCP server using `type: local` and merged-array `command:` syntax.
- [ ] `.opencode/agents/` contains 24 markdown files, one per agent currently in `.github/agents-openrouter/`, each with valid Opencode frontmatter.
- [ ] Every migrated agent's `model:` field uses the Opencode OpenRouter provider-prefixed format confirmed in Task 2 (e.g. `openrouter/moonshotai/kimi-k2`, `openrouter/qwen/qwen3.6-plus`, `openrouter/z.ai/glm-5.1` — exact IDs subject to Task 2 confirmation).
- [ ] No migrated agent uses the deprecated Copilot-prefixed tool names (`github/...`); all GitHub API operations route through `gh` CLI via the `bash` permission.
- [ ] The orchestrator's `permission.task` block explicitly allow-lists every sub-agent it can dispatch and denies all others.
- [ ] The Synthesizing Reviewer / Researcher / Auditor agents have `permission.task` set to deny everything (file-persisted dispatch only).
- [ ] `.opencode/rules/chromadb.md` exists with `globs: ["src/**/*.py"]` frontmatter and reproduces the content of `.github/instructions/chromadb.instructions.md`.
- [ ] `opencode.json` declares `"plugin": ["opencode-rules@latest"]` and the plugin loads without error on `opencode` startup.
- [ ] Running `opencode run "@orchestrator-v3 read PR #N and summarise the review"` (or equivalent simple ad-hoc task) executes end-to-end without errors and produces a comparable result to the Copilot equivalent.
- [ ] Running a full Synthesized Review under Opencode against an existing PR produces three raw reports plus a synthesis file in `.github/notes/reviews/`, matching the layout produced under Copilot.
- [ ] ChromaDB queries (e.g. `chroma_query_documents`) work from inside an Opencode agent session against the existing `.chromadb/` data.
- [ ] `.github/agents-openrouter/`, `.github/agents-copilot/`, `.github/skills/`, `.github/instructions/`, `.github/mcp.json`, and `.vscode/mcp.json` are unchanged — Copilot and the OpenRouter VS Code agents continue to work for any team member who has not switched.
- [ ] A new `docs/features/opencode-runtime.md` documents the Opencode setup, the directory layout, and the dual-run policy.

## Resolved Design Decisions

- **Q1 (resolved): `tavily` and `context7` are user-level.** They are not committed to `.github/mcp.json` or `.vscode/mcp.json`. They must NOT be added to the project `opencode.json`. Task 2 will document the entries that each developer must add to their personal `~/.config/opencode/opencode.json`.
- **Q2 (resolved): Provider is OpenRouter.** The source of truth is `.github/agents-openrouter/` (not `.github/agents-copilot/`). Opencode will be configured to use OpenRouter via its OpenAI-compatible endpoint (`https://openrouter.ai/api/v1`). The three models in use are `MoonshotAI: Kimi K2.6`, `Qwen: Qwen3.6 Plus`, and `Z.ai: GLM 5.1`. Task 2 must confirm the exact OpenRouter model slug for each (e.g. `moonshotai/kimi-k2`, `qwen/qwen3.6-plus`, `zhipuai/glm-5.1`) before agent frontmatter is written.
- **Q3 (resolved): GitHub operations via `gh` CLI.** The Orchestrator V3's `github/...` tool calls in the prompt body are replaced with equivalent `gh` CLI commands executed through `permission.bash`. No GitHub MCP server is needed.
- **Q4 (resolved): Browser agent's `agent-browser` CLI is confirmed.** Its invocation path is unchanged — shell command via `permission.bash`.

## Related

- Research: [.github/research/copilot-to-opencode-migration-2026-04-29.md](../../../.github/research/copilot-to-opencode-migration-2026-04-29.md)
- Existing migration precedent: [docs/planning/opencode-migration/prd.md](../opencode-migration/prd.md) — note this is an _earlier_, separate migration that moved away from a previous `.opencode/` runtime; the current migration re-introduces an `.opencode/` runtime for development agents only, not for the story-generation pipeline.
- ADR (to be created in this PR): [009 — Opencode as Primary Agent Runtime](../adr/009-opencode-as-primary-agent-runtime.md)
- Research synthesis source: 3-model consensus (Claude Opus 4.6, GPT-5.4, Gemini 3.1 Pro), agreement score 8/10
