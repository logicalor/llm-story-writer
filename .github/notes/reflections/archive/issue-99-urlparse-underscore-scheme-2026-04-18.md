---
date: "2026-04-18"
issue: 99
pr: 101
category: agent
targets:
  - ".github/notes/gotchas.md"
  - ".github/agents/test-writer.agent.md"
severity: minor
status: archived
archived_at: "archive/issue-99-urlparse-underscore-scheme-2026-04-18.md"
---

## Python `urlparse` silently drops underscore URI schemes — missing positive-path tests

### Finding

During issue #99 (PR #101, remove unsupported cloud providers), the URI parsing logic in
`ModelConfig.from_string()` used `urlparse()` to extract the scheme from strings like
`lm_studio://host/path` and `llama_cpp://host/path`. Python's `urlparse` silently returns an
empty `.scheme` for any URI whose scheme contains underscores — it does not raise an exception.
The entire URI is then parsed as a path, causing provider re-validation to fail silently.

The fix (splitting on `"://"` before calling `urlparse`) was identified by the Gemini reviewer
but missed by Claude and GPT. The root cause of the regression going undetected was that no
positive-path tests existed for `lm_studio://` or `llama_cpp://` URI forms — only negative-path
(invalid input) tests were present. A positive-path test for any of these schemes would have
caught the breakage immediately.

### Observation

Two distinct gaps compounded each other:

1. **Coder gap (Python gotcha):** `urlparse` behaviour on non-standard schemes is not obvious
   from the standard library documentation. RFC 3986 §3.1 restricts scheme characters to
   `[A-Za-z][A-Za-z0-9+\-.]` — underscores are invalid. `urlparse` silently accepts
   non-conformant input by returning empty `.scheme` instead of raising. This is a genuine
   Python footgun: the code appears correct, produces no exception, and only breaks specific
   inputs that test suites rarely exercise exhaustively.

2. **Test Writer gap (missing positive-path coverage):** When a function accepts URI-format
   strings with project-specific custom schemes, the Test Writer routinely writes negative-path
   tests (invalid scheme, missing host, wrong prefix) but misses explicit positive-path tests
   for each supported scheme. A single `test_from_string_lm_studio_scheme_resolves()` would
   have detected the `urlparse` failure before the branch was ever reviewed.

### Suggested Improvement

**Improvement 1:** Add gotcha #006 to `gotchas.md` documenting the `urlparse` underscore
limitation with the correct workaround.

**Improvement 2:** Add a note to the Test Writer's "Write Tests" section reminding that custom
URI schemes — especially those with underscores — require at least one positive-path test per
supported scheme to prevent silent parsing regressions.

### Action Taken

Applied:
- Added gotcha #006 to `gotchas.md` — `urlparse` silently drops underscore URI schemes.
- Added "Custom URI schemes" note to Test Writer agent "Write Tests" section.
