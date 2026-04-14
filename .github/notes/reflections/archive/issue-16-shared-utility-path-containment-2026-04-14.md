---
date: "2026-04-14"
issue: 16
pr: 52
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: active
---

## Coder Rule 9 should explicitly cover shared utility functions with path-component parameters

### Finding

During issue #16 (PR #52), the new shared utility `_wiki.py` contained a `find_pages()` function vulnerable to path traversal via three vectors: the `slug` parameter (used in directory path construction), the `glob` pattern parameter (could escape the wiki directory), and the `page_type` parameter (used as a subdirectory name). All three were user-influenced and none were validated.

The Synthesized Review caught this as ★★★ Critical (unanimous). The fix applied slug regex validation (`^[a-z0-9_-]+$`), glob containment (reject `..` and `/`), page_type allowlist validation, and belt-and-suspenders `is_relative_to()` on resolved paths.

### Observation

Coder Rule 9 currently says: "When resolving **user-provided names** to file paths, always validate the resolved absolute path starts with the intended base directory using `resolved.resolve()` and `.is_relative_to(base)`."

This covers the direct case (user gives a filename → resolve → validate). But `find_pages()` demonstrates a subtler pattern: a **shared utility function** that takes several parameters which are each used as **path components** (not full paths). The developer may not recognise these as path-traversal vectors because they're not "user-provided file names" — they're filter parameters like `slug`, `glob`, and `type`.

The existing Rule 9 text is sufficient in principle (`is_relative_to` would catch the final resolved path), but the intermediate parameters also needed individual validation to prevent glob-based escapes and directory injection. Adding a clarifying example strengthens the rule without changing its scope.

### Suggested Improvement

Add a fourth sub-bullet to Coder Rule 9:

```markdown
   - **Shared utility path components:** When writing shared functions (e.g., `_wiki.py`, `_io.py`) that accept parameters used as directory names, glob patterns, or path segments, validate each component individually — not just the final resolved path. Reject `..`, `/`, and characters outside the expected set. Apply `is_relative_to()` as a belt-and-suspenders final check.
```

### Action Taken

Applied: added fourth sub-bullet to Coder Rule 9 in `.github/agents/coder.agent.md`.
