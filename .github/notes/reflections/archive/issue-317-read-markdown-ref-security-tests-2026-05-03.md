---
date: "2026-05-03"
issue: 317
pr: 329
category: agent
targets:
  - "tests/unit/test_persist.py"
severity: minor
status: active
---

## `read_markdown_ref` security validation paths not covered by tests

### Finding

PR #329 (issue #317) added 7 unit tests in `tests/unit/test_persist.py` covering
`persist_markdown` and `read_markdown_ref`. The security validation in `persist_markdown` is
well-tested: `test_rejects_path_traversal` and `test_rejects_absolute_path` both confirm that
`_validate_relative_path` raises `ValueError` for `..` and `/`-prefixed inputs.

However, `read_markdown_ref` also calls `_validate_relative_path(relative_path)` on the `$ref`
value extracted from a pointer dict — and this call path has no corresponding test. There are no
tests verifying that `read_markdown_ref(tmp_path, {"$ref": "../evil.md"})` or
`read_markdown_ref(tmp_path, {"$ref": "/etc/passwd"})` raise `ValueError`.

### Observation

A crafted pointer dict reaching `read_markdown_ref` with a traversal or absolute path is a
realistic attack vector when pointer dicts are read from user-controlled or untrusted storage. The
validation code is present and correct, but untested. Without a test, a future refactor could
silently remove the `_validate_relative_path` call from `read_markdown_ref` without any test
failure, creating a path-traversal vulnerability.

The general pattern: whenever a security guard exists in a function, ALL entry points to that guard
must be tested independently — even when the guard is implemented via a shared helper. Tests of
function A do not cover function B even when both call the same shared validator.

### Suggested Improvement

Add two tests to `TestReadMarkdownRef` in `tests/unit/test_persist.py`:

```python
def test_rejects_traversal_in_pointer(self, tmp_path) -> None:
    with pytest.raises(ValueError):
        read_markdown_ref(tmp_path, {"$ref": "../evil.md"})

def test_rejects_absolute_path_in_pointer(self, tmp_path) -> None:
    with pytest.raises(ValueError):
        read_markdown_ref(tmp_path, {"$ref": "/etc/passwd"})
```

These can be added in a follow-up commit on this branch or in a later hardening PR.

### Action Taken

Proposed: two additional test cases for `TestReadMarkdownRef` to verify security validation
through the `read_markdown_ref` entry point. Follow-up PR or branch commit needed.
Archived as pending follow-up — active note remains until tests are added.
