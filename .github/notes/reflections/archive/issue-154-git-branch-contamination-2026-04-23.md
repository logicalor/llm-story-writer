---
date: "2026-04-23"
issue: 154
pr: 155
category: instruction
targets:
  - ".github/agents/_shared/local-workflow.md"
  - ".github/agents/orchestrator-v3.agent.md"
severity: minor
status: active
---

## Pre-existing local modifications are swept into feature branches on checkout

### Finding

When `git checkout {branch}` is run after `git add -A` with uncommitted changes, the staged
changes travel with you to the new branch. During this task, out-of-scope files that had
pre-existing local modifications were silently included in the feature branch's first commit
because `git status --porcelain` was not run after checkout.

### Observation

This is a standard Git behaviour, not a bug — but it is easy to miss. The risk is that changes
from a previous investigation, partial experiment, or unrelated fix become part of the current
PR without review. These out-of-scope changes inflate the diff, confuse reviewers, and can
introduce regressions from unfinished work.

The mitigation is a mandatory `git status --porcelain` audit immediately after checking out the
new feature branch, before the first commit. Any unexpected files must be stashed or reverted
and documented in the handoff summary.

### Suggested Improvement

Add a "Feature Branch Contamination Check" advisory section to `local-workflow.md`, and add a
step to the Orchestrator's Step 2 branch-checkout procedure.

### Action Taken

Applied: added contamination-check section to `.github/agents/_shared/local-workflow.md`
and a post-checkout audit step to Step 2 of `.github/agents/orchestrator-v3.agent.md`.
