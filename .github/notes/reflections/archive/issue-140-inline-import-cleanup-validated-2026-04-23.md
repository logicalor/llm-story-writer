---
date: "2026-04-23"
issue: 140
pr: 143
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## Inline import cleanup validated — issue-138 improvement prevented recurrence

### Finding

Issue #140 (PR #143, `fix/issue-140-move-inline-imports-story-assembler`) was a mechanical cleanup task: move all inline (function-body) imports in `story_assembler.py` to module level. This issue was created as a direct follow-up from the review of PR #139 (issue #138), which deferred the style finding as "consistent with pre-existing file pattern" and tracked the full cleanup separately.

The cleanup was straightforward: three imports moved from function bodies to the module-level import block, import ordering maintained (stdlib → third-party → local), ruff/mypy passing after the change, and tests confirming no regressions.

### Observation

The issue-138 improvement (Rule 7 sub-bullet: "place new imports at module level regardless of pre-existing inline style debt") was applied before PR #143. The cleanup was executed cleanly with no new inline import instances introduced during the fix. The pipeline worked as intended:

1. PR review identified pre-existing inline import debt (issue #138)
2. New import added at module level (not matching the debt)
3. Follow-up issue #140 created to clean up pre-existing inline imports
4. PR #143 executed the cleanup mechanically

This constitutes a minimal-overhead validation of the issue-138 improvement: the Coder did not re-introduce inline imports during the cleanup PR itself. No additional guidance is needed at this time.

The one observable friction point is that a trivial three-line style cleanup required a full issue → branch → PR → review cycle. This is appropriate given the project's quality gates, but it is worth tracking: if inline import debt accumulates in multiple files due to the same root pattern, batching such cleanups into a single "style debt sweep" PR (rather than one per file) would reduce overhead without sacrificing quality.

### Suggested Improvement

No agent changes needed — issue-138 rule already covers the root cause. However, add a note to the Coder's Rule 11 "Out-of-scope observations" guidance that encourages batching style-debt cleanup across multiple affected files into a single follow-up issue when the pattern is file-level rather than logic-level:

> **Batching style-debt cleanups:** When recording an out-of-scope style observation (inline imports, naming convention, trailing whitespace), check whether the same pattern exists in sibling files before noting it. If it does, scope the follow-up observation to cover all affected files in a single note — do not record one observation per file. State clearly which files are in scope so the Orchestrator can create a single batched follow-up issue rather than one per file.

### Action Taken

Applied: added "Batching style-debt cleanups" sub-bullet to Rule 11 in `.github/agents/coder.agent.md` — when recording an out-of-scope style observation, check sibling files for the same pattern and scope the follow-up observation to cover all affected files.
