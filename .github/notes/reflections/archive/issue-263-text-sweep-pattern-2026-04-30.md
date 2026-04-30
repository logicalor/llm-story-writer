---
date: "2026-04-30"
issue: 263
pr: 271
category: agent
targets:
  - ".opencode/agents/coder.md"
  - ".opencode/agents/orchestrator-v3.md"
  - ".opencode/agents/planner.md"
  - ".opencode/agents/documenter.md"
severity: minor
status: archived
---

## Stale Directory References in Text Sweeps

### Finding

The PR swept `.opencode/tools/` references from four Opencode agent files, but several residual references to concepts and shorthand not explicitly listed in the issue persisted. Reviewers flagged a "TS wrapper" mention in `coder.md` line 160, and the `review-checklist.md` still contains Zod and TypeScript wrapper verbiage.

### Observation

When deleting a directory, the issue description focused on explicit path mentions (e.g., "TypeScript OpenCode tool wrappers in `.opencode/tools/`"). However, shorthand forms ("TS wrapper"), table cells (`docs/tools.md` description), and parenthetical examples in code-pattern prose were not included in the original issue but were flagged during review. This shows that text sweeps need to cover not just full paths but all surface forms of a retired concept.

### Suggested Improvement

Add a new sub-bullet to Coder Rule 6 (text-sweep rules): "When retiring a concept or directory, grep for the old term's shorthand, acronym, and partial forms (e.g., 'TS wrapper', 'TypeScript wrapper', 'tool-name.ts') across all agent and instruction files, not just the full path."

### Action Taken

Applied: Removed duplicate sub-bullet in `.opencode/agents/coder.md` Rule 6 (the "When retiring a directory or concept" bullet had been inserted twice during the PR). The text-sweep rule now appears once, correctly. Reflection note archived.
