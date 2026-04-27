# Agent System — Quick Reference

This directory contains all agent definition files (`.agent.md`) for this project. Each file defines a VS Code Copilot custom agent — its name, description, allowed models, available tools, and instructions.

---

## User-Invocable Agents

These agents are invoked directly by the user and orchestrate their own work or coordinate other agents.

| Agent | File | Purpose |
| --- | --- | --- |
| **Orchestrator V3** | `orchestrator-v3.agent.md` | Feature-based workflow manager — full GitHub-auditable lifecycle (issue → branch → code → tests → review → PR) |
| **Planner** | `planner.agent.md` | Product-level planning — PRDs, task breakdowns, ADRs, feature specs (never writes code) |
| **Contemplator** | `contemplator.agent.md` | Reflects on project state, synthesises recent activity, proposes prioritised GitHub issues |
| **Auditor** | `auditor.agent.md` | Healthcheck and compliance audit — 7-phase deep audit against the project plan and ADRs |
| **Synthesizing Auditor** | `synthesizing-auditor.agent.md` | Cross-model audit coordinator — dispatches to three LLMs and synthesises consensus findings |
| **Synthesizing Researcher** | `synthesizing-researcher.agent.md` | Cross-model research coordinator — dispatches to three LLMs and synthesises consensus research |
| **PR Reviewer** | `pr-reviewer.agent.md` | Standalone ad-hoc PR reviewer — fetches and reviews pull requests outside the Orchestrator workflow |
| **Sprint Runner** | `sprint-runner.agent.md` | Batch issue dispatcher — collates open issues and dispatches Orchestrator sequentially per issue |

---

## Worker Sub-Agents (Orchestrator-Dispatched)

These agents are dispatched by the Orchestrator V3 (or Synthesizing agents) and should not be invoked directly by the user unless testing or debugging.

| Agent | File | Purpose |
| --- | --- | --- |
| **Coder** | `coder.agent.md` | Implements code changes; dispatched by Orchestrator during implementation phase |
| **Test Writer** | `test-writer.agent.md` | Writes verification tests after implementation; confirms each test passes |
| **Documenter** | `documenter.agent.md` | Maintains `docs/` after verification is confirmed; commits documentation changes |
| **Browser** | `browser.agent.md` | Browser automation via agent-browser CLI — page inspection, screenshots, E2E test development |
| **Reflection** | `reflection.agent.md` | Applies learnings from completed tasks to agent/skill/instruction files |
| **Researcher** | `researcher.agent.md` | Codebase and web research — returns compact summaries for Orchestrator planning |
| **Synthesizing Reviewer** | `synthesizing-reviewer.agent.md` | Cross-model local code review — dispatches three reviewers and synthesises consensus findings |

---

## Model-Specific Sub-Agent Files

The following 9 files are intentionally **byte-identical** to their parent agents except for the `model:` field in their YAML frontmatter. They exist so the Synthesizing agents can dispatch the same workflow to three different LLMs simultaneously — enabling cross-model consensus analysis.

| File | Parent Agent | Model |
| --- | --- | --- |
| `auditor-claude.agent.md` | Auditor | Claude Opus 4.6 |
| `auditor-gpt.agent.md` | Auditor | GPT 5.4 |
| `auditor-gemini.agent.md` | Auditor | Gemini 3.1 Pro (Preview) |
| `researcher-claude.agent.md` | Researcher | Claude Opus 4.6 |
| `researcher-gpt.agent.md` | Researcher | GPT 5.4 |
| `researcher-gemini.agent.md` | Researcher | Gemini 3.1 Pro (Preview) |
| `reviewer-claude.agent.md` | Synthesizing Reviewer | Claude Opus 4.6 |
| `reviewer-gpt.agent.md` | Synthesizing Reviewer | GPT 5.4 |
| `reviewer-gemini.agent.md` | Synthesizing Reviewer | Gemini 3.1 Pro (Preview) |

> **`model:` field format**: Always a single scalar string — arrays are not supported by the Copilot CLI. Use the human-readable hosted model name with the `(copilot)` suffix, e.g. `Claude Opus 4.6 (copilot)`, `GPT-5.4 (copilot)`, `Gemini 3.1 Pro (Preview) (copilot)`. Never use API model IDs or array syntax.

> **When editing a parent agent** (Auditor, Researcher, Synthesizing Reviewer), apply the same changes to all three model-specific variants to keep them in sync.

---

## Shared Files (`_shared/`)

Shared behavioural rules imported by multiple agents:

| File | Purpose |
| --- | --- |
| `_shared/local-workflow.md` | Critical prohibitions and local-first git workflow (non-negotiable) |
| `_shared/repo-context.md` | Repository identity lookup and project notes protocol |
| `_shared/dispatch-retry.md` | Retry protocol for agent dispatch failures |
| `_shared/audit-process.md` | 7-phase audit methodology shared by all auditor agents |
| `_shared/code-review-process.md` | Local code review checklist and output format |
| `_shared/pr-review-process.md` | PR review checklist and comment format |
| `_shared/research-process.md` | Research methodology and tool selection guide |

---

## How the Orchestrator Dispatches Agents

The standard feature-based workflow managed by **Orchestrator V3**:

```
Step 1  Issue         — Orchestrator creates/locates a GitHub issue
Step 2  Branch        — Orchestrator creates a feature branch
Step 3  Plan          — Orchestrator → Researcher (codebase research)
Step 4  Implement     — Orchestrator → Coder
Step 5  Verify        — Orchestrator → Test Writer, then runs tests
Step 6  Document      — Orchestrator → Documenter (commits docs)
Step 7  Review        — Orchestrator → Synthesizing Reviewer → Reviewer (Copilot)
Step 8  Reflect       — Orchestrator → Reflection
Step 9  Deploy        — Orchestrator monitors production deployment
```

The Orchestrator **owns all git/GitHub operations** (commit, push, create PR) except:
- **Documenter** — commits documentation changes to the feature branch (Step 6)
- All other workers return changes without committing
