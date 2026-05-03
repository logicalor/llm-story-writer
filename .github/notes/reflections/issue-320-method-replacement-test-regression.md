<!-- STALE — archived to archive/issue-320-method-replacement-test-regression-2026-05-03.md — delete this file -->
---
date: "2026-05-03"
issue: 320
pr: 332
category: agent
targets:
  - ".github/agents-copilot/coder.agent.md"
  - ".github/agents-openrouter/coder.agent.md"
severity: minor
---

## Patched method replaced by new method — existing mocks verify dead code path

### Finding

PR #332 (issue #320) refactored the orchestrator to call `FinalEditorAgent.edit_single_chapter()`
directly in a per-chapter loop, replacing the previous single-dispatch call to
`FinalEditorAgent.run()`. Two existing tests —
`test_final_edit_phase_invokes_agent` and `test_final_edit_exception_does_not_abort_assembly` —
both patched `FinalEditorAgent.run` via `@patch("...FinalEditorAgent.run")` and asserted it was
called. After the refactor, neither test failed: the patch intercepted nothing (the real `run()`
is no longer called), the mocked path was dead, and both tests passed with zero coverage of the
new `edit_single_chapter` call path. The Orchestrator diagnosed and fixed both tests after the
Test Writer's full suite run revealed them.

### Observation

The pattern is predictable: when a method that was the primary dispatch target of an orchestrator
or controller is replaced by a new method, every test that `patch()`-es the old method by name
becomes a dead mock. The test continues to pass — nothing now calls the old method so the mock
never fires, but a patched `MagicMock` that is never called still satisfies most standard
assertions (unless the test asserts `.called` or `assert_called_with`). In this case the tests
DID assert `.called`, so they would have failed — but only after the full suite run, not during
the Coder's implementation pass. The Coder did not scan existing tests for patches of the
replaced method before finishing.

The general rule: before submitting any change that removes or renames a method that was previously
the primary dispatch target, grep existing tests for patches/mocks of the old method name and
update them in the same dispatch.

### Suggested Improvement

Add a bullet to Rule 11 in both Coder agent files, under the "Test expectation drift"
sub-section, immediately after the pointer-format drift bullet:

> **When adding a new method to a class that replaces the role of an existing method** — scan
> existing tests for `patch` / `MagicMock` calls targeting the old method by name. Tests that
> mock the old method and assert `.called`, `.call_count`, or `.assert_called_with(...)` now
> verify a dead code path: the implementation no longer calls the old method, so the mock never
> fires. These tests pass silently with zero coverage of the new path. Before finishing, run:
> `grep -r "patch.*OldMethodName\|mock.*OldMethodName" tests/` and update each match to target
> the new method, adjusting assertions to match the new calling convention. (Source: issue #320,
> PR #332 — `test_final_edit_phase_invokes_agent` and
> `test_final_edit_exception_does_not_abort_assembly` both patched `FinalEditorAgent.run`; after
> the orchestrator was refactored to call `edit_single_chapter`, the mocks were inert but both
> tests passed.)

### Action Taken

Applied: added bullet to Rule 11 test-expectation-drift sub-section in both Coder agent files.
