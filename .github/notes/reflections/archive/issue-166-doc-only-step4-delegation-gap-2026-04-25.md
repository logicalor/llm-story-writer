---
date: "2026-04-25"
issue: 166
pr: 177
category: agent
targets:
  - ".github/agents/orchestrator-v3.agent.md"
severity: major
status: archived
---

## Documentation-only issues: Step 4 skip instruction is silent on who makes the changes

### Finding

Issue #166 (PR #177) was a documentation-only task: README.md, `.github/copilot-instructions.md`, `docs/manual.md`, and a new `docs/planning/opencode-migration/SUPERSEDED.md`. The Orchestrator correctly skipped Step 4 (no Coder dispatch) and despatched the Documenter at Step 6.

However, the current Step 4 skip instruction reads:

> "Skip this step for config/agent/skill/documentation-only changes … Proceed directly to Step 5."

It says nothing about _who_ will make the documentation changes. Step 6 then says:

> "After verification is confirmed, dispatch to the `Documenter` agent … It will: 1. Review the issue, PR, and code changes …"

Step 6 frames the Documenter as a post-implementation supplementary agent, not the primary implementer. For documentation-only issues there are no code changes to review — the Documenter's charter becomes ambiguous.

### Observation

Without an explicit clause, the Orchestrator must infer that Step 6's Documenter dispatch doubles as the implementation step for doc-only work. That inference is correct but not stated — agents relying on the literal wording would have the Documenter reviewing phantom "code changes" and writing supplementary docs for nothing.

Two patterns are muddled together under Step 6:

1. **Code-first pattern**: Coder writes code → Documenter documents the code changes.
2. **Doc-first pattern**: Documenter IS the implementer — there is no preceding code-Coder step.

This is especially confusing when the doc-only issue touches `.github/copilot-instructions.md` (technically an agent-instructions file owned by neither Coder nor Documenter by convention, but handled as documentation in practice).

### Suggested Improvement

In Step 4, after the skip instruction, add a delegation note:

```
For documentation-only issues where the primary deliverables are documentation files
(`docs/`, `README.md`, `AGENTS.md`, `.github/copilot-instructions.md`, or similar),
the changes will be made by the Documenter at Step 6. The Documenter is acting as
the primary implementer for this issue — not just the supplementary documentarian.
Proceed to Step 5 (lint quality gate only), then Step 6.
```

In Step 6, add a bracketed mode note before the dispatch:

```
> **Documentation-only issues:** The Documenter is dispatched here as the *primary
> implementer*, not just to supplement code changes. Pass it the full task description,
> acceptance criteria, and file list from Step 3.
```

### Action Taken

Proposed for approval — structural workflow clarification affects delegation chain for an entire class of issues.
