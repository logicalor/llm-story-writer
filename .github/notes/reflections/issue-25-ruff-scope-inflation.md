---
date: "2026-04-16"
issue: 25
pr: 72
category: agent
targets:
  - ".github/agents/orchestrator-v3.agent.md"
severity: minor
status: active
---

## Ruff formatting from prior work bundled in branch — scope inflation recurrence

### Finding

During issue #25 (Context Budgeting & Wiki Skills), the `test_compaction_plugin.py` file had unrelated ruff formatting changes bundled in the branch. These were pre-existing changes from prior development work, not introduced by the current task's Coder dispatch.

### Observation

This is the **fourth** scope inflation variant observed:

1. **Issue #5** — Auto-formatter changes mixed with functional commits (Coder Rule 8)
2. **Issue #16** — Line-ending normalization artefacts from `git checkout` (proposed Step 5d check)
3. **Issue #21** — Pre-commit hook auto-formatting 156 legacy files
4. **Issue #25** — Pre-existing formatting changes from prior work carried into new branch

The issue #25 variant is distinct from issue #21: the formatting changes were already in the working tree *before* the branch was created, carried forward from a prior development session. This means the proposed Step 5d scope validation (issue #16) would catch this because the unrelated changes would appear in `git diff --stat` before commit.

This variant is also related to the issue #11 reflection file leakage pattern — artefacts from prior sessions silently entering the next issue's commit. The root cause is the same: no clean-slate verification at branch creation time.

### Suggested Improvement

No new proposal — this variant is covered by the pending issue #16 Step 5d scope validation proposal. When applied, the scope check would flag `test_compaction_plugin.py` as unexpected in a skills-only PR.

### Action Taken

No action needed — recurrence of known scope inflation pattern, covered by pending issue #16 proposal.
