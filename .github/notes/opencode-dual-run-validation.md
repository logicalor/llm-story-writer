---
date: 2026-04-29
issue: "233"
method: static-structural
migration-issues: "229, 230, 231, 232"
---

# Opencode Dual-Run Validation Report

**Date:** 2026-04-29  
**Issue:** [#233](https://github.com/logicalor/llm-story-writer/issues/233)  
**Branch:** feat/issue-233-dual-run-validation  
**Validated by:** GitHub Copilot Orchestrator V3

## Validation Methodology

This validation was performed from within GitHub Copilot (Orchestrator V3 mode) rather than the Opencode TUI. Full end-to-end lifecycle testing (Steps 1–8 of the Orchestrator V3 workflow) requires live Opencode execution and is noted below as `not-tested-this-cycle`.

Static structural analysis covers:

1. **Inventory** — `.opencode/agents/` contains exactly 24 files matching the `.github/agents-openrouter/` source inventory.
2. **Frontmatter validity** — Each agent file has the required Opencode fields: `description`, `model`, `mode`, `permission`.
3. **Model ID correctness** — Each model ID matches the confirmed slugs in `.github/notes/opencode-provider-mapping.md`.
4. **Mode correctness** — Each agent's `mode` matches the tasks.md specification.
5. **Permission scope** — Each agent's `permission.task` structure matches its intended capability scope.
6. **Migration acceptance** — Migration issues [#228](https://github.com/logicalor/llm-story-writer/issues/228), [#229](https://github.com/logicalor/llm-story-writer/issues/229), [#230](https://github.com/logicalor/llm-story-writer/issues/230), [#231](https://github.com/logicalor/llm-story-writer/issues/231), and [#232](https://github.com/logicalor/llm-story-writer/issues/232) are closed, and the current agent inventory matches the accepted migration batches recorded in `docs/planning/copilot-to-opencode-migration/tasks.md`.

**Pass verdict:** All six criteria above met.  
**Fail verdict:** Any structural parse failure, model mismatch, mode deviation, or permission-scope deviation.  
**Not-tested-this-cycle:** Live Opencode TUI invocation, sub-agent dispatch, and ChromaDB queries from inside agent sessions.

---

## Inventory Check

`.opencode/agents/` contains **24 agent files** (plus `.gitkeep`).  
`.github/agents-openrouter/` contains **24 `.agent.md` source files** (plus `README.md`).  
Inventory parity: ✅

---

## Per-Agent Validation

| Agent | Migration Task | Mode | Model | permission.task | Hidden | Structural | Verdict |
|-------|---------------|------|-------|-----------------|--------|------------|---------|
| orchestrator-v3 | [#228](https://github.com/logicalor/llm-story-writer/issues/228) | primary | `openrouter/moonshotai/kimi-k2.6` | explicit allowlist | — | valid frontmatter | **pass** |
| coder | [#229](https://github.com/logicalor/llm-story-writer/issues/229) | subagent | `openrouter/moonshotai/kimi-k2.6` | deny | `false` | valid frontmatter | **pass** |
| test-writer | [#229](https://github.com/logicalor/llm-story-writer/issues/229) | subagent | `openrouter/moonshotai/kimi-k2.6` | deny | `false` | valid frontmatter | **pass** |
| documenter | [#229](https://github.com/logicalor/llm-story-writer/issues/229) | subagent | `openrouter/moonshotai/kimi-k2.6` | deny | `false` | valid frontmatter | **pass** |
| browser | [#229](https://github.com/logicalor/llm-story-writer/issues/229) | subagent | `openrouter/moonshotai/kimi-k2.6` | deny | `false` | valid frontmatter | **pass** |
| reflection | [#229](https://github.com/logicalor/llm-story-writer/issues/229) | subagent | `openrouter/moonshotai/kimi-k2.6` | deny | `false` | valid frontmatter | **pass** |
| reviewer-kimi | [#230](https://github.com/logicalor/llm-story-writer/issues/230) | subagent | `openrouter/moonshotai/kimi-k2.6` | deny | — | valid frontmatter | **pass** |
| reviewer-qwen | [#230](https://github.com/logicalor/llm-story-writer/issues/230) | subagent | `openrouter/qwen/qwen3.6-plus` | deny | — | valid frontmatter | **pass** |
| reviewer-glm | [#230](https://github.com/logicalor/llm-story-writer/issues/230) | subagent | `openrouter/z-ai/glm-5.1` | deny | — | valid frontmatter | **pass** |
| synthesizing-reviewer | [#230](https://github.com/logicalor/llm-story-writer/issues/230) | subagent | `openrouter/moonshotai/kimi-k2.6` | deny | — | valid frontmatter | **pass** |
| pr-reviewer | [#230](https://github.com/logicalor/llm-story-writer/issues/230) | primary | `openrouter/moonshotai/kimi-k2.6` | deny | — | valid frontmatter | **pass** |
| researcher-kimi | [#231](https://github.com/logicalor/llm-story-writer/issues/231) | subagent | `openrouter/moonshotai/kimi-k2.6` | deny | — | valid frontmatter | **pass** |
| researcher-qwen | [#231](https://github.com/logicalor/llm-story-writer/issues/231) | subagent | `openrouter/qwen/qwen3.6-plus` | deny | — | valid frontmatter | **pass** |
| researcher-glm | [#231](https://github.com/logicalor/llm-story-writer/issues/231) | subagent | `openrouter/z-ai/glm-5.1` | deny | — | valid frontmatter | **pass** |
| researcher | [#231](https://github.com/logicalor/llm-story-writer/issues/231) | primary | `openrouter/moonshotai/kimi-k2.6` | deny | — | valid frontmatter | **pass** |
| synthesizing-researcher | [#231](https://github.com/logicalor/llm-story-writer/issues/231) | primary | `openrouter/moonshotai/kimi-k2.6` | explicit allowlist | — | valid frontmatter | **pass** |
| auditor-kimi | [#232](https://github.com/logicalor/llm-story-writer/issues/232) | subagent | `openrouter/moonshotai/kimi-k2.6` | deny | — | valid frontmatter | **pass** |
| auditor-qwen | [#232](https://github.com/logicalor/llm-story-writer/issues/232) | subagent | `openrouter/qwen/qwen3.6-plus` | deny | — | valid frontmatter | **pass** |
| auditor-glm | [#232](https://github.com/logicalor/llm-story-writer/issues/232) | subagent | `openrouter/z-ai/glm-5.1` | deny | — | valid frontmatter | **pass** |
| auditor | [#232](https://github.com/logicalor/llm-story-writer/issues/232) | primary | `openrouter/moonshotai/kimi-k2.6` | explicit allowlist | — | valid frontmatter | **pass** |
| synthesizing-auditor | [#232](https://github.com/logicalor/llm-story-writer/issues/232) | primary | `openrouter/moonshotai/kimi-k2.6` | explicit allowlist | — | valid frontmatter | **pass** |
| planner | [#232](https://github.com/logicalor/llm-story-writer/issues/232) | primary | `openrouter/moonshotai/kimi-k2.6` | explicit allowlist | — | valid frontmatter | **pass** |
| contemplator | [#232](https://github.com/logicalor/llm-story-writer/issues/232) | primary | `openrouter/moonshotai/kimi-k2.6` | explicit allowlist | — | valid frontmatter | **pass** |
| sprint-runner | [#232](https://github.com/logicalor/llm-story-writer/issues/232) | primary | `openrouter/moonshotai/kimi-k2.6` | explicit allowlist | — | invalid YAML frontmatter: mis-indented `permission.bash.allow` and `permission.task.allow` lists prevent parsing | **fail** |

---

## Key Agent Outcomes

### Orchestrator V3
**Verdict: pass**  
`.opencode/agents/orchestrator-v3.md` exists with `model: openrouter/moonshotai/kimi-k2.6`, `mode: primary`, and a parseable `permission.task` allowlist. The allowlist contains exactly the specialist agents it is expected to dispatch in the migrated workflow: Test Writer, Coder, Reviewer Qwen, Reviewer Kimi, Reviewer Glm, Synthesizing Reviewer, Pr Reviewer, Documenter, Browser, and Reflection.

### Synthesizing Researcher
**Verdict: pass**  
`.opencode/agents/synthesizing-researcher.md` exists with `model: openrouter/moonshotai/kimi-k2.6`, `mode: primary`, and an explicit `permission.task` allowlist limited to Researcher Kimi, Researcher Qwen, and Researcher Glm. Its tool scope includes Tavily MCP, Context7, and ChromaDB, which matches the intended role of dispatching the three researcher sub-agents and synthesizing their outputs without widening task permissions.

### Auditor
**Verdict: pass**  
`.opencode/agents/auditor.md` exists with `model: openrouter/moonshotai/kimi-k2.6`, `mode: primary`, and an explicit `permission.task` allowlist of Researcher, Browser, and Reflection. `.opencode/agents/synthesizing-auditor.md` also exists with `model: openrouter/moonshotai/kimi-k2.6`, `mode: primary`, and an explicit `permission.task` allowlist of Auditor Kimi, Auditor Qwen, Auditor Glm, and Reflection, preserving the intended depth-1 audit-synthesis topology.

---

## Items Requiring Live Opencode Testing

The following items from the tasks.md Task 9 specification require live Opencode TUI execution. They were not performed in this cycle because GitHub Copilot orchestration context does not support Opencode agent invocation.

| Item | Source | Status |
|------|--------|--------|
| Orchestrator V3 full lifecycle (Steps 1–8) against a real trivial issue | tasks.md Task 9 | not-tested-this-cycle |
| Synthesizing Researcher end-to-end against a small research brief | tasks.md Task 9 | not-tested-this-cycle |
| Auditor quick healthcheck invocation | tasks.md Task 9 | not-tested-this-cycle |
| ChromaDB recall queries from inside agent sessions | tasks.md Task 9 | not-tested-this-cycle |
| Planner edit-scope smoke test (attempted edit outside `docs/planning/`) | tasks.md Task 8 AC | not-tested-this-cycle |

These items should be validated in a dedicated Opencode session after the feature branch is merged.

---

## Findings

**Structural failures:** 1 — `.opencode/agents/sprint-runner.md` frontmatter does not parse as YAML because two list blocks are mis-indented.  
**Model ID mismatches:** none  
**Mode deviations:** none among parseable files  
**Permission scope deviations:** none among parseable files; `sprint-runner.md` could not be fully validated because the frontmatter is invalid  
**Follow-up issues:** one fix required to repair `sprint-runner.md` frontmatter before a full static pass can be recorded

---

## Summary

| Verdict | Count |
|---------|-------|
| pass | 23 |
| fail | 1 |
| not-tested-this-cycle | 0 (see "Items Requiring Live Opencode Testing") |

Static structural validation passes for 23 of 24 migrated agents. The only failure is `.opencode/agents/sprint-runner.md`, whose frontmatter is not valid YAML and therefore fails the baseline Opencode frontmatter criterion. No `.github/agents-openrouter/` or `.github/agents-copilot/` files were modified during this validation, so dual-run integrity is preserved.