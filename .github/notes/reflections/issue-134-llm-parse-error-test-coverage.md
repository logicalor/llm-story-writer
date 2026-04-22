---
date: "2026-04-23"
issue: 134
pr: 141
category: agent
targets:
  - ".github/agents/test-writer.agent.md"
severity: minor
status: active
---

## Test Writer omits LLM-response JSON parse-error path tests

### Finding

During issue #134 (PR #141, `feat/issue-134-scene-writer-scrub-voice-ops`), the Test Writer wrote 7 tests for the new `scrub-analyze` and `voice-analyze` operations in `scene_writer.py`, but omitted `test_voice_analyze_json_parse_error_exits`. The `voice-analyze` operation calls an LLM and parses the response as JSON; if `json.loads()` fails, the tool is expected to exit with a non-zero code. This exit path had no test coverage until the post-review fix pass.

The gap was caught unanimously by all three code reviewers. The Test Writer's existing guidance covers argparse validation errors (`returncode == 2`), infrastructure adapter error paths (issue #85 proposal), and graceful degradation paths (issue #92), but contains no explicit rule about testing LLM-response JSON decode failures.

### Observation

CLI tool operations that call an LLM and then parse the response as JSON have a distinct and predictable failure mode: `json.loads()` raises `JSONDecodeError` when the LLM returns malformed output (hallucinated text, truncated tokens, empty string). The caller typically wraps this in a `try/except` and calls `sys.exit(1)`. This failure mode is not covered by:

- The "infrastructure adapter error paths" guidance (which addresses HTTP-level failures and provider classes)
- The "CLI validation assertions" guidance (which addresses argparse argument parsing)
- The "error handling" priority level (which is present but too general to trigger LLM-parse-path awareness)

The absence is structural: the Test Writer has named guidance blocks for every known error-path category *except* LLM-output parsing. Reviewers caught the gap; the Test Writer should have too.

### Suggested Improvement

Add a named guidance block for LLM-response parse-error paths to the Test Writer's "Write Tests" section, after the existing "Custom URI schemes" block:

```markdown
**LLM-response parse-error paths:** When writing tests for CLI tool operations that send a prompt to an LLM and parse the response as JSON (`json.loads()`), always include a test for the JSON decode failure path. Mock the LLM call to return a non-JSON string (e.g., `"not valid json"` or `""`), and assert the process exits with a non-zero return code (typically 1). Name these tests `test_<operation>_json_parse_error_exits`. This exit path is as mandatory as the happy path — reviewers will flag its absence unanimously. A tool that lacks this test has unverified error handling on a failure mode that LLMs produce regularly.
```

### Action Taken

Applied: added "LLM-response parse-error paths" named block to `.github/agents/test-writer.agent.md` after the "Custom URI schemes" block.
