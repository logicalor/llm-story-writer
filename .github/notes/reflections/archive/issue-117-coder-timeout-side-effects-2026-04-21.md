---
date: "2026-04-21"
issue: 117
pr: 118
category: agent
targets:
  - ".github/agents/_shared/dispatch-retry.md"
severity: minor
status: archived
---

## Timeout failures should check for side effects before retrying

### Finding

During issue #117 (PR #118), the Coder subagent completed all implementation work (file changes present on disk) but timed out before returning a report. The Orchestrator correctly followed the dispatch-retry.md protocol: checked for side effects, found them, and proceeded with verification rather than re-dispatching. This validated that the Empty Response Handling section covers the case, but the protocol is ambiguous — the "Timeout failures" bullet in the initial retryable-errors list sends readers directly to the retry protocol without first checking for completed work.

### Observation

There are two distinct timeout scenarios:

1. **Timeout before work begins or partway through** — no side effects. Retry is correct.
2. **Timeout after work completes** — side effects present. Retrying dispatches the agent against already-completed work, risking double-writes, duplicate commits, or conflicted state.

The current dispatch-retry.md structure lists timeout failures as retryable (correct for scenario 1) but does not instruct the reader to distinguish scenario 2. An Orchestrator following the protocol literally could retry a completed dispatch unnecessarily. The Empty Response Handling section below handles this correctly, but its connection to timeout cases is implicit.

### Suggested Improvement

Add a "Timeout with Possible Completion" subsection to dispatch-retry.md immediately before the Empty Response Handling section, and add a cross-reference note beside the "Timeout failures" bullet.

### Action Taken

Applied: added cross-reference note to the "Timeout failures" bullet and a "Timeout with Possible Completion" subsection to `.github/agents/_shared/dispatch-retry.md`.
