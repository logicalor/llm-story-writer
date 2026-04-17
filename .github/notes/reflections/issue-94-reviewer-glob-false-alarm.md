---
status: moved
archived_at: "archive/issue-94-reviewer-glob-false-alarm-2026-04-17.md"
---

> This note has been archived. See `archive/issue-94-reviewer-glob-false-alarm-2026-04-17.md`.

## Reviewer file glob verification can produce false negatives

### Finding

During PR #95's review cycle, all three reviewer sub-agents confirmed writing their report files to disk, but an `ls` glob check subsequently returned no results. The files were present — the glob pattern failed in the terminal tool rather than the files being absent.

This false negative would have triggered unnecessary re-dispatching of reviewer agents, wasting significant time.

### Observation

The Orchestrator's Step 7 Phase B says "verify the report files exist on disk before proceeding" but does not specify how to verify. Glob patterns like `ls .github/notes/reviews/*-claude-raw.md` can fail in the terminal tool even when the target files exist (e.g., due to shell glob expansion issues in subprocess contexts, or the tool not finding the cwd). Using exact file paths avoids this class of false alarm.

The correct verification pattern is to use exact, absolute-or-relative paths rather than glob expansion:
```bash
ls .github/notes/reviews/2026-04-17-pr95-claude-raw.md
```
or
```bash
test -f .github/notes/reviews/2026-04-17-pr95-claude-raw.md && echo "exists"
```

### Suggested Improvement

Update the Step 7 Phase B verification sentence in `orchestrator-v3.agent.md` to specify exact-path verification:

**Before:**
> After all three complete, verify the report files exist on disk before proceeding.

**After:**
> After all three complete, verify the report files exist on disk before proceeding. Use exact file paths (`ls path/to/file` or `test -f path/to/file && echo "exists"`) rather than glob patterns — glob expansion in the terminal tool can return no results even when files are present.

### Action Taken

Applied: updated Step 7 Phase B verification sentence in `.github/agents/orchestrator-v3.agent.md`.
