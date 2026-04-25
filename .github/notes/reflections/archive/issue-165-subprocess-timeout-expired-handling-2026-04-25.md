---
date: "2026-04-25"
issue: 165
pr: 176
category: agent
targets:
  - ".github/agents/test-writer.agent.md"
severity: minor
status: archived
---

## subprocess.TimeoutExpired must be caught and converted to pytest.fail()

### Finding

`tests/integration/test_end_to_end_headless.py` called `subprocess.run(timeout=600)` without
wrapping in `try/except subprocess.TimeoutExpired`. Both Claude and Gemini flagged this
independently in the synthesis. When the timeout fires, Python raises the exception before
returning a result object — pytest records the event as an ERROR, not a FAIL. All stdout/stderr
captured up to that point is trapped in the exception's `.stdout` / `.stderr` bytes attributes
and is never printed. This makes diagnosing a real timeout failure require a second full run.

Additionally, any `assert elapsed <= TIMEOUT_SECONDS` placed after `subprocess.run` with a
timeout is unreachable dead code — execution only reaches it when the process has already
returned within budget.

### Observation

The test-writer.agent.md contains guidance for many subprocess patterns (e.g. argparse exit
codes, custom URI schemes) but has no guidance for subprocess timeout handling. This is the
first E2E subprocess integration test in the suite, so the pattern hadn't been needed before.
Its absence made it easy for the implementation to miss the `try/except` wrapper.

### Suggested Improvement

Add a named block to the Write Tests section of `test-writer.agent.md` covering:
- Always wrap `subprocess.run(timeout=N)` in `try/except subprocess.TimeoutExpired`
- Call `pytest.fail()` with truncated stdout/stderr from `e.stdout` / `e.stderr`
- Note that `.stdout` / `.stderr` are `bytes | None` when using `capture_output=True`
- Note that `assert elapsed <= timeout` after an unwrapped call is unreachable dead code

### Action Taken

Applied: added "subprocess.TimeoutExpired handling" named block to the Write Tests section of
`.github/agents/test-writer.agent.md`.
