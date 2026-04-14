---
date: "2026-04-14"
issue: 14
pr: 56
category: agent
targets:
  - ".github/agents/_shared/review-checklist.md"
severity: minor
status: archived
---

## Batch operations need extra review scrutiny — 3 distinct rollback/sync gaps in one tool

### Finding

During issue #14 (Build wiki-update Tool), the Synthesized Review found 3 distinct atomicity gaps specifically in the batch operation (`cmd_batch`), while standalone operations (create, update, delete) were solid:

1. **Missing index backup** — batch did not snapshot the wiki index before starting, so a mid-batch failure left a partially-updated index with no way to roll back.
2. **No index sync after batch** — batch called individual create/update/delete operations that each sync their own state, but the batch wrapper did not perform a final consistency sync of the wiki index after all operations completed.
3. **Import `re` in loop body** — `re` module was imported inside the loop body of the batch processor rather than at module level, causing repeated import lookups (minor, but symptomatic of hasty batch implementation).

### Observation

This is a pattern: standalone CRUD operations are implemented with proper atomicity (atomic writes, path validation, error handling), but when a batch/composite operation wraps them, the orchestration layer (rollback, pre-flight snapshots, post-completion sync) is neglected. The Coder focuses on getting each individual operation right — learned behaviour from Rules 9 and 10 — but does not apply the same rigour to the wrapping operation that coordinates them.

The review checklist (Phase 2, Data Access) mentions "Migrations have proper rollback support" but has nothing about batch/composite operation atomicity in tool code. The Coder agent has no guidance on batch operations. The reviewer agents catch these reliably (all 3 were flagged), but earlier detection by the Coder would save a review-fix cycle.

This is the first batch operation in the codebase, so the pattern is new. If more batch operations are built, this will recur.

### Suggested Improvement

Add a checklist item to `.github/agents/_shared/review-checklist.md` under Phase 2 (Code Review) → Data Access:

```markdown
- [ ] **Batch/composite operations** — if a function wraps multiple state-changing operations, verify: (1) pre-flight snapshot or backup is taken before the batch starts, (2) failures mid-batch trigger rollback or at minimum leave state consistent, (3) a final sync/consistency check runs after the batch completes
```

This is a minor addition to an existing checklist — no structural change.

### Action Taken

Applied: added batch/composite operations checklist item to review-checklist.md Phase 2 Data Access section.
