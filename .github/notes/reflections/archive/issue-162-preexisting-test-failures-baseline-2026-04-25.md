---
date: "2026-04-25"
issue: 162
pr: 172
category: instruction
targets:
  - ".github/notes/deferred.md"
severity: minor
status: archived
---

## Pre-existing test failures: new file confirmed + baseline verification technique

### Finding

During PR #172 testing, `tests/unit/test_story_assembler_generate_handoff.py` was confirmed as
a pre-existing failure baseline — the test failures exist on `development` before this PR's
changes are applied. Combined with the 19 failures previously documented for
`test_story_state_tool.py` and `test_wiki_extract_tool.py` (issue #160), the project now has
at least three test files with known pre-existing failures.

Additionally, PR #172 surfaced a concrete verification technique for confirming whether any
test failure is pre-existing:

```bash
git stash && pytest tests/unit/test_X.py -v && git stash pop
```

If the failures reproduce on the stashed (pre-PR) state, they are baseline failures.

### Observation

The issue-160 pre-existing failure note added an entry to `deferred.md` but did not include:
1. `test_story_assembler_generate_handoff.py` as a known-failing file.
2. The `git stash` verification technique — reviewers must currently determine baseline status
   by other means (grepping git log, reading PR descriptions, or manual branch comparison).

### Suggested Improvement

Update the `deferred.md` entry to:
1. Add `test_story_assembler_generate_handoff.py` to the list of known pre-existing failures.
2. Add the `git stash && pytest ... && git stash pop` verification command.

### Action Taken

Applied: updated the deferred.md entry "Fix pre-existing test failures" to add the new file
and the git stash verification technique.
