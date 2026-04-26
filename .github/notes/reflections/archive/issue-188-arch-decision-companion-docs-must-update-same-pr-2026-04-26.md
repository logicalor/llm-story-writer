---
date: "2026-04-26"
issue: 188
pr: 201
category: agent
targets:
  - ".github/agents/documenter.agent.md"
  - ".github/agents/orchestrator-v3.agent.md"
severity: major
status: archived
---

## Architecture decision PRs must update companion documents in the same PR

### Finding

ADR 008 formally retired `src/application/services/` as an architectural layer. At the time of merge, four high-visibility developer-facing and agent-facing documents still actively instructed agents and developers to use the retired layer:

- `AGENTS.md` (line 16): "src/application/ → Services, strategies (use cases)"
- `.github/copilot-instructions.md` (line 25): "src/application/ (services, strategies)"
- `docs/tools.md` (line 136): "if it is orchestration-only, in src/application/services/"
- `docs/manual.md` (line 59): "src/application/ → Services, strategies (use cases, depends on domain)"

All four stale references were confirmed on disk by Gemini during the synthesized review. Two of them (`AGENTS.md` and `.github/copilot-instructions.md`) are read by agents at runtime and directly influence code generation decisions — meaning the contradiction was operationally active, not merely cosmetic documentation debt.

This is consistent with a recurring pattern across documentation-only PRs: the primary deliverable (the ADR or feature doc) is carefully written and reviewed, while the companion documents that derive descriptions from the architecture are not swept in the same pass. Similar stale-ref patterns were observed in issues #166, #169, and #173.

### Observation

Documentation-only architectural decision PRs have a narrower blast radius than code PRs, but a wider documentation surface — they require updating _more_ companion files because they change the canonical description of a layer, pattern, or component that is referenced across multiple separate documents.

The current Documenter workflow (Step 3 "Determine Documentation Needs") has a table that maps change types to documentation actions. The "Architecture change" row currently reads `Update docs/architecture.md`. This is incomplete: it does not prompt the Documenter to sweep the four high-traffic companion files (`AGENTS.md`, `.github/copilot-instructions.md`, `docs/manual.md`, `docs/tools.md`) for references to the changed architectural component.

Because these files each serve a different audience (agents, Copilot assistant, end-user manual, tool guide), stale references in them propagate inconsistency across different context windows after the PR is merged.

The existing Step 4 skip instruction and Step 6 documentation-only note (added in issue #166) correctly established who does the work — but neither specifies the _scope_ of the documentation sweep for architecture decisions.

### Suggested Improvement

**`documenter.agent.md` Step 2 (Determine Documentation Needs):**

Extend the "Architecture change" and "New ADR" rows in the documentation actions table to include a mandatory companion-document sweep:

> "**For architecture changes that retire, introduce, or rename a layer, component, or tool pattern:** after updating the primary documentation target, sweep these four companion files for stale references to the changed component and update them in the same commit:
> - `AGENTS.md` — architecture layers section
> - `.github/copilot-instructions.md` — stack overview or architecture section
> - `docs/manual.md` — architecture or layer descriptions
> - `docs/tools.md` — implementation routing guidance
>
> The sweep must cover both prose descriptions and table cells. Use `grep -rn '<old-term>' AGENTS.md .github/copilot-instructions.md docs/manual.md docs/tools.md` to locate all occurrences."

**`orchestrator-v3.agent.md` Step 6 documentation-only note:**

After the existing "Documentation-only issues" dispatch note, add:

> "For documentation-only issues that introduce an ADR or record an architecture decision: instruct the Documenter to run a companion-document sweep across `AGENTS.md`, `.github/copilot-instructions.md`, `docs/manual.md`, and `docs/tools.md`, updating all references to the changed architectural component. This sweep is required in the same PR — stale references in these files take effect immediately upon merge."

### Action Taken

Applied (2026-04-26): 
- `documenter.agent.md` Step 2 table — Architecture change and New ADR rows extended with "**and run companion-document sweep** (see below)". Added new subsection "Architecture decision companion-document sweep" with `grep` command template and rationale, citing source.
- `orchestrator-v3.agent.md` Step 6 — Added blockquote "Architecture decision companion sweep (ADR PRs)" immediately after the documentation-only dispatch note, requiring Documenter to sweep all four companion files in the same PR.
