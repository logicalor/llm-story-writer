---
date: "2026-04-15"
issue: 18
pr: 64
category: agent
targets:
  - ".github/agents/documenter.agent.md"
severity: minor
status: active
---

## Documenter `gh` auth gap — 3rd+ occurrence

### Finding

During issue #18 (Build Outline Planner Subagent), the Documenter could not post PR comments because `gh` was not authorized. This was resolved manually by the user. Same gap as issue #13 (reflection active, major proposal pending) and issue #20 (archived as recurrence).

### Observation

This is at least the **third** occurrence of the Documenter lacking GitHub access for PR comments:

1. **Issue #13** — original finding, major proposal to add GitHub MCP tools to Documenter (`issue-13-documenter-github-access.md`, status: active, pending approval)
2. **Issue #20** — recurrence, archived (`issue-20-documenter-github-access-recurrence-2026-04-15.md`)
3. **Issue #18** — this occurrence, resolved by user authorizing `gh`

The issue #13 proposal to add `github/issue_read`, `github/pull_request_read`, and `github/add_issue_comment` to the Documenter's tools array remains the correct fix. Each occurrence costs a manual intervention by the user. Three occurrences establishes this as a consistent friction point rather than a one-off.

### Suggested Improvement

No new proposal — the issue #13 reflection already proposes the correct fix. This recurrence strengthens the case for prioritising approval of that proposal.

### Action Taken

No action needed — recurrence of known gap recorded for prioritisation evidence. The issue #13 proposal remains the pending fix.
