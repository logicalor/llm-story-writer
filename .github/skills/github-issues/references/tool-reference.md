# GitHub Issues — Tool Reference

## Tool Inventory

| Operation | Tool | Key parameters |
| --- | --- | --- |
| Fetch a single issue | `github/issue_read` | `method: "get"`, `owner`, `repo`, `issue_number` |
| Get issue comments | `github/issue_read` | `method: "get_comments"`, `owner`, `repo`, `issue_number` |
| Search for issues | `github/search_issues` | `query`, `owner`, `repo` |
| List issues (filtered) | `github/list_issues` | `owner`, `repo`, optional `state`, `labels` |
| Create a new issue | `github/issue_write` | `method: "create"`, `owner`, `repo`, `title`, `body` |
| Update an existing issue | `github/issue_write` | `method: "update"`, `owner`, `repo`, `issue_number` |
| Comment on an issue | `github/add_issue_comment` | `owner`, `repo`, `issue_number`, `body` |

**There is no `github/create_issue` or `github/get_issue` tool.**

## Decision Flowchart

```
Do you have an issue number?
├── YES → Do you want to read it?
│         ├── YES → github/issue_read (method: "get")
│         └── NO  → Do you want to update it?
│                   ├── YES → github/issue_write (method: "update", issue_number: N)
│                   └── NO  → Do you want to comment on it?
│                             └── YES → github/add_issue_comment (issue_number: N)
└── NO  → Do you want to find an issue?
          ├── YES → github/search_issues (query with keywords)
          │         or github/list_issues (browse by state/label)
          └── NO  → Do you want to create one?
                    └── YES → github/issue_write (method: "create")
```

## Search Query Syntax

| Goal | Query string |
| --- | --- |
| Open issues matching keywords | `"tenant domain" state:open` |
| Closed issues matching keywords | `"password reset" state:closed` |
| Issues with a specific label | `label:bug state:open` |
| Issues by assignee | `assignee:username state:open` |
| Broad keyword search | `"document upload"` |

## Common Mistakes

1. **Searching by issue number** — `number:` is NOT a valid GitHub qualifier. If you have the number, use `github/issue_read`.
2. **Adding `is:issue`** — the search tool already scopes to issues.
3. **Adding `repo:owner/repo` in query** — use the `owner`/`repo` parameters instead.
4. **Missing `issue_number` on update** — required when using `method: "update"`.
