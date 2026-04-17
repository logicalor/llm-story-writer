---
date: "2026-04-16"
issue: 69
pr: 71
category: agent
targets:
  - ".github/agents/orchestrator-v3.agent.md"
severity: minor
status: active
---

## Stale local development branch caused inaccurate diff scope

### Finding

During issue #69 (Add behavioral tests for compaction plugin), the local `development` branch was behind `origin/development`, causing `git diff development...HEAD` to include changes from prior PRs already merged upstream. The workaround was using `origin/development` explicitly in diff commands to get an accurate scope of changes for the current PR.

### Observation

This is an operational issue that can affect any step using diff commands — Step 5d (working tree audit), Step 7 (review), and Step 8 (finalise). If the local tracking branch is stale, diffs show a superset of the actual PR changes, which can:

1. Inflate the review scope with irrelevant changes
2. Cause the working tree audit to flag files not part of the current task
3. Mislead the Synthesized Review into evaluating changes from prior PRs

The fix is simple: ensure `git fetch origin` is run before any diff comparison, and use `origin/development` (or the remote-tracking ref) instead of the local branch name when computing diffs.

The Orchestrator's Step 1 already includes branch creation (`git checkout -b feat/...`) but does not include `git fetch origin` to ensure the base branch is current. Adding a fetch before branching would prevent this category of issue.

### Suggested Improvement

Add `git fetch origin` to the Orchestrator's Step 1 (Setup), before branch creation:

```markdown
git fetch origin
git checkout -b feat/issue-{N}-{slug} origin/development
```

This ensures the feature branch is always based on the latest remote state, and subsequent diffs against `origin/development` are accurate.

This is a minor operational improvement — no structural change to the workflow, just an additional git command.

### Action Taken

No action needed — first occurrence recorded. If recurrence observed, apply the suggested Step 1 amendment.
