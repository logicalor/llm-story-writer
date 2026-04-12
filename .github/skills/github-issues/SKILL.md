---
name: github-issues
description: Guide for working with GitHub issues via MCP tools. Use this when fetching, searching, creating, updating, or commenting on GitHub issues. Covers correct tool selection, required parameters, query syntax, and common pitfalls.
license: MIT
---

## GitHub Issues — MCP Tool Reference

> This skill covers the correct way to interact with GitHub issues using the MCP GitHub tools. Follow this guide to avoid common mistakes with tool names, parameters, and query syntax.

---

## Prerequisites

Before making **any** GitHub API call:

1. Read `.github/notes/repo.md` to obtain `OWNER` and `REPO`.
2. If the file is missing, run `git remote get-url origin`, parse the owner and repo, and record them.
3. Use these values for every `owner` and `repo` parameter below.

---

## Tool Inventory

For the full tool inventory table, query syntax, and common mistakes, see [tool reference](./references/tool-reference.md).

---

## Fetching a Single Issue by Number

When you already have an issue number (e.g., the user says "work on issue #42"), use `github/issue_read` — **do not search for it**.

```
github/issue_read
  method: "get"
  owner: "{OWNER}"
  repo: "{REPO}"
  issue_number: 42
```

This returns the issue title, body, labels, state, assignees, and other metadata.

### Common mistake — NEVER search by issue number

If you have an issue number, **do not use `github/search_issues`**. All of these are wrong:

- `query: "#42"` — searches full text for the string "#42"
- `query: "42"` — searches full text for the string "42"
- `query: "number:42"` — `number:` is not a valid GitHub search qualifier
- `query: "is:issue number:42"` — `number:` is not a valid GitHub search qualifier
- `query: "is:issue 42"` — searches full text, may return unrelated results

None of these reliably find issue #42. **The only correct way to fetch a known issue is:**

```
github/issue_read
  method: "get"
  owner: "{OWNER}"
  repo: "{REPO}"
  issue_number: 42
```

---

## Searching for Issues

Use `github/search_issues` when you need to find issues by keyword, label, or state. The search is **already scoped to `is:issue`** — do not add `is:issue` to your query.

### Required parameters

- `query` (string) — GitHub search syntax (see below)
- `owner` (string) — optional but recommended to scope to your repo
- `repo` (string) — optional but recommended to scope to your repo

### Query syntax examples

| Goal                                    | Query string                           |
| --------------------------------------- | -------------------------------------- |
| Open issues matching keywords           | `"tenant domain" state:open`           |
| Closed issues matching keywords         | `"password reset" state:closed`        |
| Issues with a specific label            | `label:bug state:open`                 |
| Issues by assignee                      | `assignee:username state:open`         |
| Broad keyword search (open + closed)    | `"document upload"`                    |

### Common mistakes

1. **Searching by issue number** — `number:` is NOT a valid GitHub search qualifier. Queries like `number:42`, `is:issue number:42`, or `#42` will fail or return wrong results. If you have the issue number, use `github/issue_read` with `method: "get"` instead.
2. **Adding `is:issue`** — the tool already scopes to issues. Adding it again is harmless but redundant.
3. **Adding `repo:owner/repo`** — use the `owner` and `repo` parameters instead. Adding `repo:` in the query alongside `owner`/`repo` parameters can cause conflicts.
4. **Overly specific queries** — GitHub search is full-text. Use 2–3 key terms, not full sentences.

### Example: Check for existing issues before creating

```
github/search_issues
  query: "tenant custom domain state:open"
  owner: "{OWNER}"
  repo: "{REPO}"
```

If results come back, review them. If a matching issue exists, use it instead of creating a duplicate.

---

## Listing Issues

Use `github/list_issues` to get a paginated list of issues, optionally filtered by state and labels. This is useful for browsing all open issues or issues with a specific label.

```
github/list_issues
  owner: "{OWNER}"
  repo: "{REPO}"
  state: "OPEN"
  labels: ["feature"]
  perPage: 20
```

Note: The `state` parameter uses uppercase values: `"OPEN"` or `"CLOSED"`.

---

## Creating a New Issue

Use `github/issue_write` with `method: "create"`. There is **no** `github/create_issue` tool.

### Required parameters

- `method`: `"create"`
- `owner`: `"{OWNER}"`
- `repo`: `"{REPO}"`
- `title`: concise feature/bug description

### Recommended parameters

- `body`: full context, acceptance criteria, related issues
- `labels`: `["feature"]` or `["bug"]` as appropriate

### Example

```
github/issue_write
  method: "create"
  owner: "{OWNER}"
  repo: "{REPO}"
  title: "Add tenant custom domain support"
  body: |
    ## Context
    Tenants need to configure custom domains for their panel instances.

    ## Acceptance Criteria
    - [ ] Tenant settings page shows domain field
    - [ ] Domain validation and DNS verification
    - [ ] Tests covering happy path and validation errors
  labels: ["feature"]
```

### Extracting the issue number

The tool returns a response containing a `url` field like `https://github.com/OWNER/REPO/issues/123`. Parse the issue number (123) from the URL — it is the last numeric segment after `/issues/`.

If the response includes a `number` field, prefer that.

---

## Updating an Issue

Use `github/issue_write` with `method: "update"`. You **must** provide `issue_number`.

### Required parameters

- `method`: `"update"`
- `owner`: `"{OWNER}"`
- `repo`: `"{REPO}"`
- `issue_number`: the issue number to update

### Example: Update body with new context

```
github/issue_write
  method: "update"
  owner: "{OWNER}"
  repo: "{REPO}"
  issue_number: 42
  body: |
    ## Updated Context
    After research, the implementation approach has been refined...
```

### Example: Close an issue

```
github/issue_write
  method: "update"
  owner: "{OWNER}"
  repo: "{REPO}"
  issue_number: 42
  state: "closed"
  state_reason: "completed"
```

### Common mistake

**Missing `issue_number`** — the update method fails with "missing required parameter: issue_number" if you omit it. Always provide the issue number when updating.

---

## Commenting on an Issue

Use `github/add_issue_comment`. This also works for pull requests (PRs are issues in GitHub's API).

```
github/add_issue_comment
  owner: "{OWNER}"
  repo: "{REPO}"
  issue_number: 42
  body: "Implementation started on branch `feat/issue-42-custom-domains`."
```

---

## Decision Flowchart

For a visual decision flowchart, see [tool reference](./references/tool-reference.md).

---

## Full Workflow Example: "Work on issue #42"

1. **Fetch the issue** to understand requirements:
   ```
   github/issue_read
     method: "get"
     owner: "{OWNER}"
     repo: "{REPO}"
     issue_number: 42
   ```

2. **Read the issue body** — extract title, acceptance criteria, and context.

3. **Add a comment** acknowledging work has started:
   ```
   github/add_issue_comment
     owner: "{OWNER}"
     repo: "{REPO}"
     issue_number: 42
     body: "Starting implementation. Branch: `feat/issue-42-short-description`."
   ```

4. **After completion**, update the issue state:
   ```
   github/issue_write
     method: "update"
     owner: "{OWNER}"
     repo: "{REPO}"
     issue_number: 42
     state: "closed"
     state_reason: "completed"
   ```

## Full Workflow Example: "Implement tenant domain support"

1. **Search for existing issues** to avoid duplicates:
   ```
   github/search_issues
     query: "tenant domain state:open"
     owner: "{OWNER}"
     repo: "{REPO}"
   ```

2. **Also search closed issues** for prior context:
   ```
   github/search_issues
     query: "tenant domain state:closed"
     owner: "{OWNER}"
     repo: "{REPO}"
   ```

3. **If no matching issue exists**, create one:
   ```
   github/issue_write
     method: "create"
     owner: "{OWNER}"
     repo: "{REPO}"
     title: "Add tenant custom domain support"
     body: "..."
     labels: ["feature"]
   ```

4. **Record the issue number** from the response and proceed.
