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

## Multi-path pipeline agents must converge all return paths through a single shared variable

### Finding

PR #157 introduced `current_outline` variable threading in `outline-planner` to fix PR #157's own regression: Phase 5 was returning `merged_outline` unconditionally on the chunked path, which discarded any refinements produced by the critique loop when `use_chunked_outline_generation=true` AND `enable_outline_critique=true` were both active. Two of three reviewers (GPT, Gemini) flagged this as Critical; Claude missed it entirely.

### Observation

When an agent workflow has multiple generation paths (chunked vs. non-chunked) combined with optional loops (critique/no-critique), returning different path-specific named variables from the final phase introduces a silent cross-product failure: any path combination that exercises both a branching path AND the optional loop will have the loop's output discarded. The root cause is always the same: a per-path variable name is used in the return spec instead of a shared variable updated by every phase.

The fix pattern — assign a shared `current_outline` variable at the start of Phase 3, update it at each phase transition, and return it unconditionally from Phase 5 — eliminates all cross-product gaps. The variable always reflects the most recent version regardless of which path was taken.

This is reviewable: a Phase N "return" clause that names different variables for different code paths is the defect signature.

### Suggested Improvement

Add a new review checklist item under Agent Instructions in the Phase 2 review section:

**Multi-path pipeline return convergence** — in workflows with multiple generation strategies AND optional loops, verify the final return phase uses a single shared variable updated through each phase, not path-specific named variables.

### Action Taken

Applied: added "Multi-path pipeline return convergence" item to the Agent Instructions section of `.github/agents/_shared/review-checklist.md`.
