---
date: "2026-04-14"
issue: 59
pr: 60
category: agent
targets:
  - ".github/agents/orchestrator-v3.agent.md"
  - ".github/notes/deferred.md"
severity: minor
status: active
---

## Review-to-issue pipeline validated; git-safe-publish.sh recurrence (6th)

### Finding

Two observations from issue #59 (defence-in-depth `/`/`\` rejection in `_validate_glob_pattern()`):

1. **Positive signal — review-to-issue pipeline works.** This issue originated from Synthesized Review finding M-S-02 on PR #58, where reviewers flagged that `_validate_glob_pattern()` lacked the slash rejection already present in `_validate_slug()`. The finding was filed as issue #59 and resolved cleanly: 2-file change, 222 tests pass, 9/10 model agreement on the synthesized review. This validates the review pipeline's ability to spawn targeted follow-up issues for real security gaps.

2. **Recurring friction — `scripts/git-safe-publish.sh` still missing.** The Orchestrator's Steps 5d, 7, and 8 reference this script. It does not exist (tracked since issue #1 in `deferred.md`). This is at least the 6th issue where manual `git add && git commit && git push` was required as a workaround. Issues #1, #4, #11, #16, and now #59 have all encountered this.

### Observation

The review-to-issue pipeline is working as designed — synthesized reviews catch genuine security consistency gaps and the resulting issues are well-scoped and quick to resolve. No agent changes needed for this path.

The `git-safe-publish.sh` gap continues to accumulate friction but is already tracked in `deferred.md`. Each occurrence costs a few minutes of manual git commands. The script remains blocked on being prioritised as a migration task.

### Suggested Improvement

No new agent or instruction changes needed. The positive review-to-issue signal confirms the current process works. The `git-safe-publish.sh` gap is already tracked — recording the recurrence here for future prioritisation evidence.

### Action Taken

No action needed — positive validation of existing pipeline. Recurrence of known deferred item recorded for prioritisation evidence.
