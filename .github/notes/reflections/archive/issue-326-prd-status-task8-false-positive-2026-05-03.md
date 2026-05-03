---
date: "2026-05-03"
issue: 326
pr: 338
category: instruction
targets:
  - "docs/planning/chromadb-source-sync/prd.md"
severity: minor
status: active
---

## PRD Status Line Claims Task 8 (Integration Test) Was Implemented — It Was Not

### Finding

During PR #338 (issue #326 — rag reconcile CLI, backfill, source-sync contract docs), the PRD status line in `docs/planning/chromadb-source-sync/prd.md` reads:

> **Status:** In progress — Tasks 1 and 2 implemented in issue #324 / PR #336; Tasks 3, 4, and **8** implemented in issue #325 / PR #337

Task 8 requires `tests/integration/test_chroma_source_sync.py`. That file does not exist — `file_search` returns no results. Neither does any test that matches the Task 8 description (edit-and-retrieve flow verifying staleness detection end-to-end).

Additionally, Tasks 5 and 7 were completed in PR #338 (issue #326) but the PRD status line was not updated to reflect this.

### Observation

The PRD status line is read by agents planning future work. A false "Task 8 done" claim could cause an agent to skip implementing the integration test, leaving a gap in coverage that is never caught. Conversely, the missing PR #338 attribution means an agent scanning the PRD won't know Tasks 5 and 7 are done.

### Suggested Improvement

Update the PRD status line to:

```
**Status:** In progress — Tasks 1 and 2 implemented in issue #324 / PR #336; Tasks 3 and 4 implemented in issue #325 / PR #337; Tasks 5 and 7 implemented in issue #326 / PR #338
```

### Action Taken

Applied: corrected the PRD status line in `docs/planning/chromadb-source-sync/prd.md` — removed the false Task 8 attribution from PR #337, added Tasks 5 and 7 attribution to PR #338.
