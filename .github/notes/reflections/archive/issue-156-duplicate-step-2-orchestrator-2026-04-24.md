---
date: "2026-04-24"
issue: 156
pr: 157
category: agent
targets:
  - ".opencode/agents/story-orchestrator.md"
severity: minor
status: archived
---

## Pre-existing duplicate step "2." in story-orchestrator.md Phase 2 not corrected by PR

### Finding

`story-orchestrator.md` Phase 2 contains two consecutive numbered list entries both labeled `2.` — one is the delegation action ("Delegate outline generation to the `outline-planner` subagent, passing: ...") and the second is a constraint note ("The `outline-planner` handles the full pipeline internally... Do **not** run critique or revision steps at the orchestrator level."). The sequence reads 1, 2, 2, 3, 4, 5, 6, 7. PR #157 modified step 4 of this same list without correcting the pre-existing duplicate.

### Observation

This is pre-existing debt that was not introduced by PR #157 but is visible to anyone reviewing the modified file. Only Claude flagged it; GPT and Gemini did not. Given that the numbered-step-continuity checklist was already established before this PR, the failure to catch it suggests the check was not applied to pre-existing lines in the same section — only to newly added lines, which is a partial application of the rule.

The second "2." is a constraint note (informational content about what the subagent handles and what NOT to do at orchestrator level), not a distinct action step. The appropriate fix is to fold it into step 2 as a note/blockquote, preserving the constraint while removing the spurious step number.

### Suggested Improvement

Convert the second "2." to a `> **Note:**` blockquote within step 2, after the config values bullet list.

### Action Taken

Applied: converted the duplicate step "2." to a `> **Note:**` block in `story-orchestrator.md` Phase 2.
