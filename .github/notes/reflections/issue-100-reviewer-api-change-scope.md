---
date: "2026-04-18"
issue: 100
pr: 102
category: instruction
targets:
  - ".github/agents/_shared/review-checklist.md"
severity: minor
status: archived
archived_at: "archive/issue-100-reviewer-api-change-scope-2026-04-18.md"
---

## Reviewer scope gap: callers of changed APIs in root-level scripts

### Finding

During PR #102 synthesis (outline strategy `rag_service` parameter removal), the GPT reviewer
caught three root-level files (`test_rag_integration.py`, `demo_rag_integration.py`,
`RAG_PROMPT_FILENAME_INTEGRATION.md`) that still referenced the removed constructor parameter.
The Claude and Gemini reviewers missed all three.

The review package included the correct diff and file list, but the Claude and Gemini reviewers
scoped their analysis to the changed files in the diff. Root-level scripts were not in the diff
(they were not modified — they still contained the broken call), so they were outside the
natural mental scope of a diff-based review.

### Observation

A changed API's callers are not in the diff unless they were updated. For a signature change,
the *broken callers* are precisely the files that should have been updated but weren't — which
means they will never appear in the diff. The review checklist (Phase 2, Code Review) has no
instruction to check callers of changed APIs outside the diff scope.

GPT's broader cross-file reasoning caught this; Claude and Gemini's narrower diff-scope review
missed it. Adding an explicit checklist item targets the reviewers who did not infer the
broader scope themselves.

### Suggested Improvement

Add a checklist item to review-checklist.md Phase 2 (Code Review, General section):

> - [ ] **API signature changes** — if a function, method, or constructor signature changed
>   (parameter added/removed/renamed), grep the workspace for callers:
>   `grep -rn 'ClassName\|function_name' . --include='*.py' --include='*.ts'`
>   Include root-level scripts (`test_*.py`, `demo_*.py`, `migrate_*.py`) — these call `src/`
>   APIs directly and are not in the diff because they were not updated.

### Action Taken

Applied: added API signature changes caller-sweep item to the General section of Phase 2 in
`.github/agents/_shared/review-checklist.md`.
