---
date: "2026-04-15"
issue: 18
pr: 64
category: agent
targets:
  - ".github/agents/_shared/code-review-process.md"
severity: minor
status: active
---

## GPT uniquely caught orchestrator overlap by checking files outside the diff

### Finding

During issue #18 (Build Outline Planner Subagent), the Synthesized Review finding S-W-01 identified that the Orchestrator's Phase 2 contained a duplicate critique loop that overlapped with the new Outline Planner subagent's Phase 4d. Only GPT caught this because it read the `story-orchestrator.md` file — which was **not** in the diff. Claude and Gemini reviewed only the changed files and missed the overlap entirely.

The finding was genuine: the orchestrator's Phase 2 still contained detailed critique-loop instructions that were now the planner's responsibility. The fix correctly updated the orchestrator to defer entirely to the planner.

### Observation

The current code review process (`.github/agents/_shared/code-review-process.md`) instructs reviewers to "Read each changed file" (prerequisite step 3) and check for "No unrelated changes" (Phase 1). This naturally focuses review on the diff. However, for **agent definitions that delegate to or are delegated by other agents**, the most important review target is often an *unchanged* file that now has overlapping or contradictory responsibilities.

GPT's behaviour — proactively reading the parent orchestrator file to verify delegation boundaries — was uniquely valuable. This is analogous to checking a parent class when a child class is introduced. Without this cross-file check, the overlap would have shipped and caused runtime confusion (both orchestrator and planner attempting the critique loop).

This is the first observation of model-specific review behaviour producing unique value from cross-file checking. Worth monitoring whether this pattern recurs. If it does, a minor clarification to the review prerequisites (adding "also read files that delegate to or depend on changed agent/skill definitions") would be warranted.

### Suggested Improvement

No process change at this time — this is a first occurrence. If cross-file checking produces unique value in 2+ future issues, consider adding a clarification to the code review prerequisite step 3:

> For agent definitions and skills, also read files they reference or delegate to (e.g., parent orchestrator, tool schemas, related subagents) — delegation boundary overlaps are invisible within the diff alone.

### Action Taken

No action needed — first occurrence recorded for pattern tracking. Will revisit if cross-file review value recurs.
