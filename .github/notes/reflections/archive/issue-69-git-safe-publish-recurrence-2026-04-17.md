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

## git-safe-publish.sh missing — 8th+ recurrence

### Finding

During issue #69 (Add behavioral tests for compaction plugin), the `scripts/git-safe-publish.sh` script referenced in the Orchestrator's Steps 5d, 7, and 8 did not exist. Manual `git add -A && git commit && git push origin {branch}` commands were required as a workaround.

### Observation

This is at least the **8th** occurrence of this friction point. Prior recurrences documented: issues #1, #4, #11, #16, #21, #59, and now #69. The script has been tracked in `.github/notes/deferred.md` since issue #1 (2026-04-12) — 4 days and 8+ issues without resolution.

The cumulative cost is now substantial. At approximately 2-3 minutes of manual git commands per occurrence across 8 issues, the total time spent on workarounds likely exceeds the time needed to create the script. The `scripts/verify-green.sh` script has the same deferred status.

### Suggested Improvement

No new agent instruction change — the deferred item already tracks this. This 8th recurrence strengthens the case for creating both scripts as a dedicated issue rather than continuing to defer.

### Action Taken

No action needed — recurrence recorded for prioritisation evidence. Supersedes issue-21-git-safe-publish-recurrence.md with updated count.
