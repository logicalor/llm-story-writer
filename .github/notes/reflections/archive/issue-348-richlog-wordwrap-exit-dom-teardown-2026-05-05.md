---
date: "2026-05-05"
issue: 348
pr: 349
category: instruction
targets:
  - ".github/notes/gotchas.md"
  - ".github/agents-copilot/test-writer.agent.md"
  - ".github/agents-openrouter/test-writer.agent.md"
severity: minor
---

## Textual TUI Testing: RichLog Word-Wrap and `call_after_refresh(self.exit)` DOM Teardown

### Finding

During issue #348 (PR #349), two Textual-specific test failures were debugged and fixed:

1. **`RichLog.write()` word-wraps output.** A test asserting the exact full message string against a `RichLog` widget's output failed because `RichLog.write()` word-wraps content at the widget's current rendering width. The fix was to assert a shorter prefix/substring rather than the complete message.

2. **`call_after_refresh(self.exit)` tears down the DOM during `pilot.pause()`.** Source code originally used `self.call_after_refresh(self.exit)` to request quit. In test context, `await pilot.pause()` runs all pending callbacks — including the deferred `exit` — which tears down the Textual DOM before subsequent assertions can execute. Reverted source to `self.exit()` directly; test patches `exit` via `patch.object(app, "exit")` to prevent actual exit during assertion phase.

### Observation

The existing Textual testing guidance (gotcha #026, test-writer.agent.md Textual section) covers `@work(thread=True)` worker patterns and inline local import patching. Neither gotcha addresses word-wrap assertion failure modes or the `call_after_refresh(self.exit)` DOM teardown race. Both are silent failure modes: the first produces a `AssertionError` with a non-obvious cause (the message exists but is wrapped); the second produces `NoMatches` or silently skips post-exit assertions.

The pre-existing failure theme recurs: this task also involved 7 pre-existing test failures (5 in `test_tui.py`, 2 in `test_consistency_checker.py`). This is the third occurrence across issues #162, #316, and #348. The major proposal to add a PRE-EXISTING FAILURE BASELINE section to `local-workflow.md` (originally proposed in #316) was never applied.

### Suggested Improvement

**Minor (applied):**
1. **gotchas.md** — Add gotcha #056 (RichLog word-wrap assertion) and #057 (call_after_refresh exit DOM teardown)
2. **test-writer.agent.md (both variants)** — Append two sub-bullets to the existing Textual `@work(thread=True)` section

**Major (proposed):**
- **local-workflow.md** — Add PRE-EXISTING FAILURE BASELINE subsection (third recurrence; see issue-316 archive for prior proposal)

### Action Taken

Applied (4 minor improvements):
- Added gotcha #056 (`RichLog.write()` word-wrap assertion) to `.github/notes/gotchas.md`
- Added gotcha #057 (`call_after_refresh(self.exit)` DOM teardown) to `.github/notes/gotchas.md`
- Added two Textual sub-bullets to `.github/agents-copilot/test-writer.agent.md`
- Added two Textual sub-bullets to `.github/agents-openrouter/test-writer.agent.md`

Proposed (major): PRE-EXISTING FAILURE BASELINE section for `.github/agents/_shared/local-workflow.md` — see report below.
