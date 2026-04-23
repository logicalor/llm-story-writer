---
date: "2026-04-24"
issue: 156
pr: 157
category: instruction
targets:
  - ".github/agents/_shared/review-checklist.md"
severity: minor
status: archived
---

## Validation guards at multiple layers must apply identical conditions

### Finding

PR #157 added validation guards at two layers: the orchestrator (Phase 2, after `outline-planner` returns) and `story-planner` (at the start, before calling `critique-runner`). The `story-planner` guard explicitly covered whitespace-only strings. The orchestrator guard initially did not, creating an asymmetry: a whitespace-only outline could pass the upstream guard and only fail one phase later, after the orchestrator may have attempted to write the empty value to story state. Two of three reviewers (GPT, Gemini) flagged this independently; Claude missed it.

### Observation

The asymmetry weakens defense-in-depth: the earlier guard is the intended first line of protection, but if its condition is a subset of the downstream guard's condition, some invalid inputs will pass through unhandled. In this case, a whitespace-only outline:
- Passes the orchestrator guard (if the guard only checks null, {}, empty string)
- Gets written to story state
- Is caught by story-planner — but only after the write has already occurred and one more subagent dispatch overhead

The fix was to standardise both guards to identical conditions. The general principle: when multiple layers guard the same invariant, read each guard condition against all others and verify they are identical.

### Suggested Improvement

Add a checklist item to the Agent Instructions section in the Phase 2 review checklist covering validation guard layer parity.

### Action Taken

Applied: added "Validation guard layer parity" item to the Agent Instructions section of `.github/agents/_shared/review-checklist.md`.
