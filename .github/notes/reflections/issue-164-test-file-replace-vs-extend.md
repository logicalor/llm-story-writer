---
date: "2026-04-25"
issue: 164
pr: 175
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## Coder replaced existing test file instead of extending it

### Finding

During PR #175, the Coder was given `test_prompt_relocation.py` as part of its dispatch scope (to add tests for the new prompt relocation). Instead of extending the file, the Coder rewrote it entirely, deleting 8 passing tests that had been written for issue #5. The Test Writer had to be re-dispatched to restore the deleted tests — an extra round-trip that would not have been necessary if the Coder had extended the file.

### Observation

Rule 11 ("Implement only the files listed in the dispatch") has a "Test expectation drift" sub-bullet that covers the case where implementation legitimately breaks existing tests. But neither that sub-bullet nor any other Coder rule states the converse: **when adding new tests to an existing test file, preserve all existing test methods**.

The Coder's natural pattern when asked to "write tests for X" is to produce a clean file from scratch. For new files this is correct; for existing files it destroys coverage. An explicit rule is needed: extend, never replace.

### Suggested Improvement

Add a sub-bullet to Rule 11 in `coder.agent.md` stating that when a test file is in dispatch scope, the Coder must read the existing file first, record all current method names, then add new methods/classes only. After writing, verify every pre-existing method name still appears. Replacing or truncating existing test content is out of scope regardless of plan wording.

### Action Taken

Applied: added "When a test file is in your dispatch scope" sub-bullet to Rule 11 in `.github/agents/coder.agent.md` with the extension-only requirement and a source attribution to this PR.
