# PR Review Process — Shared Protocol

> Shared review checklist and comment format for agents that review pull requests. Include this file in any agent that performs code reviews.

---

## Prerequisites

Before reviewing a PR:

1. **Resolve repository identity** — read `.github/notes/repo.md` for `OWNER` and `REPO`
2. **Fetch PR context** — details, diff, files, existing reviews
3. **Load project conventions** — ChromaDB query + `.github/notes/` files
4. **Create pending review** — start a GitHub review session

---

## Review Phases

### Phase 1 — Structural Review

Check the PR structure before diving into code:

- [ ] **Title** — clear, concise, follows convention (`feat:`, `fix:`, `refactor:`, etc.)
- [ ] **Description** — explains what and why, not just how
- [ ] **Linked issue** — references issue number (`Closes #N` or `Fixes #N`)
- [ ] **Branch** — named correctly (`feat/issue-N-...` or `fix/issue-N-...`)
- [ ] **Target branch** — merging into `development`, not `main`
- [ ] **Size** — reasonable scope (if >500 lines, suggest splitting)

### Phases 2–7 — Backend, Frontend, Security, Testing, Performance, Documentation

> Follow the shared review checklist in **`.github/agents/_shared/review-checklist.md`** for Phases 2–7. This file defines the complete checklists for Code, Security, Testing, Performance, and Documentation review.

---

## Comment Format

Use this format for all review comments:

```markdown
**Category:** [Security | Correctness | Performance | Style | Testing | Documentation]
**Severity:** [Critical | Warning | Suggestion]

[Description of the issue — be specific and explain why it matters]

**Suggestion:**
```
// Example fix or improvement
```

**Reference:** [Link to relevant documentation, ADR, or convention file]
```

### Severity Definitions

- **Critical** — Must be fixed before merge (security vulnerability, bug, breaking change)
- **Warning** — Should be fixed (potential bug, performance issue, convention violation)
- **Suggestion** — Nice to have (style improvement, minor optimization, documentation)

### Category Definitions

- **Security** — Vulnerabilities, authorization issues, data exposure
- **Correctness** — Bugs, logic errors, incorrect behavior
- **Performance** — N+1 queries, missing indexes, inefficient code
- **Style** — Convention violations, formatting, naming
- **Testing** — Missing tests, incorrect assertions, test quality
- **Documentation** — Missing or incorrect documentation

---

## Posting Comments

### Line-Specific Comments

Use `github/add_comment_to_pending_review` for comments on specific lines:

```
github/add_comment_to_pending_review(
  owner: "OWNER",
  repo: "REPO",
  pullNumber: N,
  path: "relative/path/to/file",
  line: 42,
  body: "**Category:** Correctness\n**Severity:** Warning\n\n...",
  subjectType: "LINE"
)
```

For multi-line comments, use `startLine` and `startSide`:

```
github_add_comment_to_pending_review(
  ...,
  startLine: 40,
  startSide: "RIGHT",
  line: 45,
  side: "RIGHT",
  ...
)
```

### File-Level Comments

Use `subjectType: "FILE"` for comments about the whole file:

```
github_add_comment_to_pending_review(
  ...,
  subjectType: "FILE",
  ...
)
```

### PR-Level Comments

Use `github/add_issue_comment` for general feedback:

```
github_add_issue_comment(
  owner: "OWNER",
  repo: "REPO",
  issue_number: N,  // PR number works as issue number
  body: "## Summary\n\n..."
)
```

---

## Submitting the Review

After adding all comments, submit the review:

```
github_pull_request_review_write(
  method: "submit_pending",
  owner: "OWNER",
  repo: "REPO",
  pullNumber: N,
  event: "COMMENT",  // Always COMMENT — never APPROVE or REQUEST_CHANGES
  body: "## Review Summary\n\n[Overall assessment]"
)
```

**Important:** The PR Reviewer agent never approves or requests changes — only posts comments. The human reviewer makes the final decision.

---

## Output Format

After completing the review, post a summary comment on the PR:

```markdown
## 🔍 PR Review Summary

**PR:** #[number] — [title]
**Reviewer:** PR Reviewer Agent
**Files Reviewed:** N
**Comments Posted:** N

### Overall Assessment

[One paragraph summary of the PR quality and any concerns]

### Findings by Category

| Category | Critical | Warning | Suggestion |
|----------|----------|---------|------------|
| Security | N | N | N |
| Correctness | N | N | N |
| Performance | N | N | N |
| Style | N | N | N |
| Testing | N | N | N |
| Documentation | N | N | N |

### Key Issues

1. **[Category]** — [Brief description] (file:line)
2. ...

### Recommendations

- [ ] [Action item 1]
- [ ] [Action item 2]

---

*Review completed using project conventions from `.github/instructions/` and `.github/notes/`.*
```

---

## Best Practices

1. **Be constructive** — every comment should include a suggestion or reference
2. **Be specific** — cite line numbers, file names, and exact issues
3. **Be consistent** — use the same format for all comments
4. **Be thorough** — review all files, don't skip large diffs
5. **Be helpful** — explain why something is an issue, not just that it is
6. **Check conventions** — use ChromaDB and `.github/notes/` for project-specific context
7. **Prioritize** — focus on Critical and Warning issues first
8. **Stay in scope** — don't suggest unrelated refactors

---

## Common Issues to Watch For

### Code Quality

- Missing input validation
- Hardcoded values that should be configurable
- Missing error handling
- Overly complex functions that should be decomposed
- Code duplication

### Security

- Missing authorization checks
- Unvalidated user input
- SQL injection (raw queries with user input)
- Sensitive data in code (credentials, API keys)
- Missing access control on new endpoints

### Testing

- Missing tests for new features
- Skipped tests
- Missing edge case tests
- Incorrect assertions

---

## After the Review

1. **Submit the review** — use `submit_pending` with `event: COMMENT`
2. **Post summary** — add top-level PR comment with overall assessment
3. **Update notes** — if new patterns or gotchas discovered, add to `.github/notes/`
4. **Embed to ChromaDB** — if significant findings, embed for future reference
