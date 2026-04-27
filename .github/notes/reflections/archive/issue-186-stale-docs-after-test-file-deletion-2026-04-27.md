---
date: "2026-04-26"
issue: 186
pr: 199
category: agent
targets:
  - ".github/agents/test-writer.agent.md"
severity: minor
status: archived
---

## Stale documentation not updated when test files were deleted

### Finding

PR #199 deleted `test_e2e_opencode.py` and `test_generate_with_retry.py`. The initial pass did not update `docs/testing/integration-tests.md` or `docs/manual.md`, both of which referenced the deleted file names explicitly. The review cycle caught both stale references and they were fixed in a follow-up commit. The Test Writer had no rule about documentation sweeps when deleting test files.

### Observation

Documentation files — especially integration test docs and user-facing manuals — frequently name test files by filename in prose, tables, and example commands. Deleting a test file without sweeping `docs/` for its name leaves stale references that mislead contributors and CI documentation audits. The Coder's Rule 6 already covers stale-docs sweeps for source file deletions, but the Test Writer has no equivalent. The pattern "delete test file → stale docs remain" is now confirmed by PR #199 as a real recurrence risk.

### Suggested Improvement

Add a guidance bullet to Step 2 "Write Tests" in `test-writer.agent.md` covering the documentation sweep required when deleting a test file: grep `docs/` for the deleted filename and update all references in the same pass.

### Action Taken

Applied: added a bold-header guidance bullet at the end of Step 2 in `test-writer.agent.md` — "Stale documentation sweep when deleting test files" — specifying the grep command and high-risk doc locations.
