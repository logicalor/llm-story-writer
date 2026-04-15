---
date: "2026-04-16"
issue: 21
pr: 66
category: agent
targets:
  - ".github/agents/orchestrator-v3.agent.md"
severity: minor
status: active
---

## git-safe-publish.sh missing — 7th+ recurrence

### Finding

During issue #21 (Build Custom Commands), the `scripts/git-safe-publish.sh` script referenced in the Orchestrator's Steps 5d, 7, and 8 did not exist. Manual `git add -A && git commit -m "..." && git push origin {branch}` commands were required as a workaround.

### Observation

This is at least the **7th** occurrence of this friction point. Prior recurrences: issues #1, #4, #11, #16, #59, and now #21. The script is tracked in `.github/notes/deferred.md` since issue #1 (2026-04-12) — 4 days and 7+ issues without resolution.

The Orchestrator and `local-workflow.md` both reference this script as if it exists. Every issue since #1 has required manual workaround commands. The cumulative friction is substantial — each occurrence costs a few minutes of manual git commands and creates a discrepancy between documented and actual workflow.

The `scripts/verify-green.sh` script has the same status — referenced but non-existent, also tracked since issue #1.

### Suggested Improvement

No new agent instruction change — the deferred item already tracks this. This recurrence strengthens the case for prioritising the creation of both scripts as an early task rather than continuing to defer.

### Action Taken

No action needed — recurrence recorded for prioritisation evidence. The deferred.md item remains the tracking location.
