---
date: "2026-04-15"
issue: 20
pr: 62
category: agent
targets:
  - ".github/agents/documenter.agent.md"
severity: major
status: archived
---

## Documenter GitHub access gap — 3rd recurrence

### Finding

During issue #20 (Build Story Orchestrator Agent), the Documenter again could not post a PR comment because it lacks GitHub API tools. The Orchestrator compensated by posting the comment itself — the same workaround used in issue #13 and at least one prior occurrence.

This is documented in the existing reflection `issue-13-documenter-github-access.md` (still active, not yet applied). This is the 3rd known occurrence of this specific gap.

### Observation

Each recurrence costs a small amount of orchestration overhead (Orchestrator must detect the failure and post the comment itself), but more importantly the workaround is undocumented in the Orchestrator's workflow — it happens ad hoc every time. The existing reflection proposes adding `github/issue_read`, `github/pull_request_read`, and `github/add_issue_comment` to the Documenter's tools array. Three occurrences provide strong evidence this should be prioritised.

### Suggested Improvement

Apply the fix proposed in `issue-13-documenter-github-access.md`: add the minimum required GitHub API tools to the Documenter agent's tools array.

### Action Taken

Deferred — major change requiring approval. Recurrence recorded as additional evidence for prioritisation.
