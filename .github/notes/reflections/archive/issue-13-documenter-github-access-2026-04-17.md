---
date: "2026-04-14"
issue: 13
pr: 49
category: agent
targets:
  - ".github/agents/documenter.agent.md"
severity: major
status: archived
---

## Documenter lacks GitHub API tools but workflow requires them

### Finding

During issue #13 (Build critique-runner Tool), the Documenter could not post a PR comment — the Orchestrator had to do it instead. This has occurred in prior issues as well.

The Documenter agent's `tools:` array is:
```
[execute, read, 'io.github.upstash/context7/*', 'chroma/*', edit, search, web, todo]
```

However, the Documenter's workflow references GitHub API tools it does not have access to:
- **Step 1 (Gather Context):** "Read the issue using `github/issue_read`" and "Read the PR using `github/read_pull_request`"
- **Step 5 (Commit and Report):** "Post a comment on the PR"
- **Rule 7:** "Post a PR comment after documentation is complete"

The Orchestrator's `tools:` array includes `github/issue_read`, `github/pull_request_read`, `github/add_issue_comment`, etc. The Documenter has none of these.

### Observation

This is an agent configuration mismatch — the workflow instructions promise capabilities the agent doesn't have. The Documenter can work around Step 1 by using `execute` to run `gh issue view` and `gh pr view` via CLI, but cannot post PR comments without the GitHub MCP tools (or the `gh` CLI, which requires separate authentication).

The Orchestrator currently compensates by posting the PR comment itself after the Documenter finishes, but this is an undocumented workaround that adds friction to every task.

### Suggested Improvement

Add the minimum required GitHub API tools to the Documenter's `tools:` array:

```yaml
tools:
  [execute, read, 'io.github.upstash/context7/*', 'chroma/*', edit, search, web, todo,
   github/issue_read, github/pull_request_read, github/add_issue_comment]
```

This gives the Documenter:
- `github/issue_read` — read issue details for context gathering (Step 1)
- `github/pull_request_read` — read PR details for context gathering (Step 1)
- `github/add_issue_comment` — post PR comments (Step 5, Rule 7)

No write/modify tools are included (no `github/update_pull_request`, `github/create_branch`, etc.) — the Documenter should only read issues/PRs and post comments.

### Action Taken

Proposed for approval — this adds new tools to an agent, changing its capabilities. Collated 2026-04-17, pending user approval.
