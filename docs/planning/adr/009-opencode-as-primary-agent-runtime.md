# ADR 009: Opencode as Primary Agent Runtime (with Copilot Dual-Run)

**Date:** 2026-04-29
**Status:** Proposed

## Context

The project's agentic development workflow currently runs through GitHub Copilot Chat in VS Code. Twenty-four custom agents exist in two variants: `.github/agents-openrouter/` (OpenRouter-hosted models — the **source of truth for this migration**) and `.github/agents-copilot/` (Copilot-routed models). Three skills in `.github/skills/`, one applyTo-scoped instruction file in `.github/instructions/`, and an MCP configuration in `.github/mcp.json` plus `.vscode/mcp.json` together implement the orchestrator-driven, multi-model-synthesised workflow that delivers issues, reviews, audits, research, and reflection.

The agents in `.github/agents-openrouter/` use three model families for multi-model synthesis: **Kimi K2.6** (MoonshotAI, primary model), **Qwen3.6 Plus** (Qwen, Qwen-family sub-agents), and **GLM 5.1** (Z.ai, GLM-family sub-agents). The chosen Opencode provider is **OpenRouter** (`https://openrouter.ai/api/v1`).

The team wants to evaluate Opencode (https://opencode.ai), an open-source terminal-first agent runtime that supports the same fundamental abstractions — agents, skills, MCP servers, and project rules — without requiring VS Code or the Copilot subscription. Migration is feasible: the 2026-04-29 multi-model research report (`.github/research/copilot-to-opencode-migration-2026-04-29.md`) confirmed that Opencode reads `.github/copilot-instructions.md` and `.agents/skills/*/SKILL.md` natively and supports near-direct equivalents for every Copilot artefact, with one gap (applyTo glob scoping) covered by a community plugin.

Three decisions need to be recorded together because they shape every downstream task:

1. Whether to migrate at all, and which runtime is canonical going forward.
2. Whether to delete the Copilot artefacts during the migration or keep both runtimes in parallel.
3. Where the Opencode agent files live, given that an earlier `.opencode/` runtime was previously deleted (PR #175 / issue #164) when the story-generation pipeline went Python-native.

## Decision

**Adopt Opencode as the primary agent runtime for development work, while preserving the Copilot artefacts in place for a dual-run period.**

The migration introduces:

- `opencode.json` at the project root as the new top-level configuration file.
- `.opencode/agents/` containing 24 migrated agent files, one per agent in `.github/agents-openrouter/` (the migration source). The multi-model reviewer/researcher/auditor sub-agents are named `reviewer-kimi`, `reviewer-qwen`, `reviewer-glm`, `researcher-kimi`, `researcher-qwen`, `researcher-glm`, `auditor-kimi`, `auditor-qwen`, `auditor-glm`.
- `.opencode/rules/` containing `applyTo`-equivalent rule files driven by the `opencode-rules` community plugin.
- No changes to `.agents/skills/` (already discovered natively by Opencode).
- No changes to `.github/agents-openrouter/`, `.github/agents-copilot/`, `.github/skills/`, `.github/instructions/`, `.github/mcp.json`, or `.vscode/mcp.json`. They stay in place during the dual-run period.

The dual-run period ends in a future, separate decision once Opencode has been demonstrated to reproduce the full Synthesized Review and Synthesized Research workflows against real PRs and research briefs. That future decision will choose one canonical runtime and remove the other set of artefacts.

The previously-deleted `.opencode/` tree (which contained TypeScript tool wrappers and story-generation prompt mirrors before the Python-native migration) is **not being recreated**. The new `.opencode/` tree contains only `agents/` and `rules/` for development work — no tools, no story-pipeline mirrors. This separation of concerns is deliberate: the story-generation pipeline runs in Python in-process; the development workflow runs through Opencode agents.

## Consequences

### Positive

- The team gains an open-source, model-agnostic runtime that does not require VS Code or a Copilot subscription. Anyone with an OpenRouter API key can run the full agent system from a terminal using the same Kimi/Qwen/GLM models already in use.
- The Synthesized Review and Synthesized Research workflows translate cleanly to Opencode's `permission.task` model. The depth-1 file-persisted dispatch pattern from PR #70 is preserved — the synthesizer's `permission.task: deny` for all entries is the structural enforcement that prevents the depth-2 nesting issue from recurring.
- Skills already live at `.agents/skills/`, which Opencode discovers natively. Zero migration effort for the skill layer.
- MCP server configuration moves into a single, validated, schema-aware file (`opencode.json`) instead of three separate JSON files (`.github/mcp.json`, `.vscode/mcp.json`, and a per-developer `~/.copilot/mcp-config.json`).
- The `opencode-rules` plugin gives `applyTo`-equivalent scoping plus extra dimensions Copilot does not have (`keywords:`, `tools:`, `agent:`, `model:`).

### Negative

- During the dual-run period, every change to an agent prompt must be applied to both runtimes (`.github/agents-openrouter/` and `.opencode/agents/`). This is the standard cost of running parallel implementations and is the explicit reason for keeping the dual-run period bounded.
- Copilot's `github/<tool-name>` tool prefix has no native Opencode equivalent. **Resolved (Q3):** those calls are replaced with equivalent `gh` CLI commands routed through `permission.bash`. This is a prompt-content edit concentrated in the Orchestrator V3 prompt body.
- Opencode's `permission.edit` does not support glob-scoped path allow-lists in a way that maps cleanly to Copilot's "this agent can only edit files in directory X" pattern. Agents like Planner that must not write production code rely on prompt-body discipline plus `edit: ask` rather than enforced file-path scoping. This is a regression in mechanical safety; it is mitigated by the dual-run validation step before either runtime is removed.
- The previously-deleted `.opencode/` tree returns under a new and narrower remit. Contributors familiar with the prior deletion must be aware that `.opencode/agents/` and `.opencode/rules/` are intentional and have a different scope from the deleted `.opencode/tools/` and `.opencode/skills/` trees. Documentation in `docs/features/opencode-runtime.md` must call this out explicitly.

### Neutral

- Model identity and tool inventories per agent are unchanged. Each migrated agent uses the same model and the same conceptual capability surface; only the schema and configuration format change.
- The shared agent rules files in `.github/agents/_shared/` are referenced by markdown reading inside agent prompts. Opencode reads markdown the same way Copilot does, so these shared files require no changes.
- `.github/copilot-instructions.md` at the project root continues to be the canonical project-rules file; both Copilot and Opencode read it.
