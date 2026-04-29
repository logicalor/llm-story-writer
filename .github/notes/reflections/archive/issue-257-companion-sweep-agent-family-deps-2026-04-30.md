---
date: "2026-04-30"
issue: 257
pr: 259
category: agent
targets:
  - ".opencode/agents/documenter.md"
  - ".github/agents-copilot/documenter.agent.md"
severity: minor
status: archived
---

## Agent-family configuration changes not in Documenter's companion-sweep decision table

### Finding

Issue #257 (PR #259) was a documentation-only fix to `docs/features/opencode-runtime.md`. The fix stated that both the researcher and auditor families carry developer-local MCP dependencies. After the initial fix was reviewed, finding S-W-01 (singular, subsequently verified and fixed) identified that `AGENTS.md` line 30 still only mentioned the researcher family — the same inaccuracy, in a separate file. The Documenter's initial dispatch did not check `AGENTS.md` because agent-family configuration changes are not listed in the decision table as a trigger for a companion-document sweep.

### Observation

The Documenter's decision table triggers a full companion-document sweep for "Architecture change" and "New ADR" rows. These sweeps include `AGENTS.md`. However, a documentation correction about which agent families carry developer-local MCP dependencies is not classified as an architecture change — it is a bug fix to a feature doc. The Documenter therefore had no signal to check `AGENTS.md` for the same claim.

`AGENTS.md` functions as the project's top-level orientation document for both developers and agent runtimes. Its runtime description section explicitly names which families carry developer-local dependencies. When a `docs/features/` file is updated to correct such a claim, `AGENTS.md` is a natural companion to check. The pattern is not unique to MCP dependencies — any agent-family configuration property documented in `docs/features/opencode-runtime.md` is likely also reflected in `AGENTS.md`.

### Suggested Improvement

Add a row to the Documenter's decision table for agent-family configuration changes, immediately before the `Bug fix with non-obvious cause` row:

```
| Agent-family configuration change (MCP tools, permissions, developer-local dependencies) | Update the relevant `docs/features/` file **and** check `AGENTS.md` for the same claim — `AGENTS.md` carries a prose description of which agent families carry developer-local MCP dependencies and is read by agents at runtime. (Source: issue #257, PR #259.) |
```

Apply to both `.opencode/agents/documenter.md` and `.github/agents-copilot/documenter.agent.md`.

### Action Taken

Applied: added "Agent-family configuration change" row to the decision table in `.opencode/agents/documenter.md` and `.github/agents-copilot/documenter.agent.md`.
