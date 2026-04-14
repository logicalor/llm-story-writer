---
date: "2026-04-14"
issue: 14
pr: 56
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: major
status: active
---

## sys.exit() in shared utilities bypasses except Exception handlers — systemic risk

### Finding

During issue #14 (Build wiki-update Tool), the `_validate_slug()` shared utility function uses `sys.exit(1)` to signal validation failure. `sys.exit()` raises `SystemExit`, which is a `BaseException` subclass — not an `Exception` subclass. Any caller using `except Exception` to handle errors will not catch this, causing the entire process to terminate unexpectedly.

The Synthesized Review flagged this as a warning. The fix replaced `sys.exit(1)` with raising a `ValueError`, which is caught by standard `except Exception` handlers.

### Observation

This is a systemic pattern risk. `sys.exit()` is commonly used in CLI entry points (the `if __name__ == "__main__"` block) where it's appropriate — it terminates the script with a status code. However, when shared utility functions (called by multiple entry points) use `sys.exit()` instead of raising exceptions, they break the caller's error handling contract.

The Coder's Rule 9 covers security validation (subprocess injection, path traversal, boundary validation, shared utility path components) but has no guidance on exception types. This is a distinct concern: correct exception hierarchy in shared code.

Existing tools in `src/tools/` use an `_error()` helper that calls `sys.exit(1)` — this pattern was established early and works correctly in standalone CLI scripts. But as shared utilities (`_wiki.py`, `_io.py`, `_llm.py`) are extracted and called from multiple tools, `sys.exit()` in shared code becomes a hazard.

A follow-up issue (#57) was created for the pre-existing `_validate_slug()` backslash case, but the systemic pattern — `sys.exit()` in shared code — is not addressed by any Coder rule.

### Suggested Improvement

Add a sub-bullet to Coder Rule 9 (Security: subprocess, path, and input validation):

```markdown
- **Exception types in shared utilities:** Shared modules (`_wiki.py`, `_io.py`, `_llm.py`, etc.) must raise exceptions (`ValueError`, `FileNotFoundError`, etc.) — never call `sys.exit()`. `sys.exit()` raises `SystemExit` (a `BaseException`), which bypasses `except Exception` handlers and terminates the process. Reserve `sys.exit()` for CLI entry points (`if __name__ == "__main__"` blocks) only.
```

This adds a fifth sub-bullet to Rule 9, covering exception hygiene in shared code.

### Action Taken

Proposed for approval — adds a new sub-bullet to Coder Rule 9, extending the rule's scope beyond security to include exception hierarchy correctness.
