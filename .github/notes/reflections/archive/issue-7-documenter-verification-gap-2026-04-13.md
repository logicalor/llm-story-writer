---
date: "2026-04-13"
issue: 7
pr: 34
category: agent
targets:
  - ".github/agents/documenter.agent.md"
severity: minor
status: archived
---

## Documenter produces inaccurate output formats and file extensions

### Finding

During issue #7 (Build savepoint-mgr Tool), the Documenter wrote documentation with `.json` file extensions and array output format for the `list` subcommand, when the actual implementation uses `.md` files and returns a dict. Both inaccuracies were caught by all three reviewers unanimously (U-W-01, U-W-02).

### Observation

The Documenter agent's verification checklist already covers route tables, method signatures, DB schema, directory trees, file paths, and links. However, it does not explicitly cover **output format/structure** (what the code actually returns) or **file extensions used by the implementation** (what files the code creates on disk). These are the exact two things the Documenter got wrong.

This is the first Documenter inaccuracy finding — not yet a recurring pattern — but the fix is trivial: add two bullet points to the existing verification checklist.

### Suggested Improvement

Add to the Documenter agent's verification checklist (the blockquote in "### 3. Write Documentation"):

```markdown
> - For tool output formats: read the Python tool's `cmd_*` functions to verify the exact JSON structure returned (dict vs array, field names, status codes).
> - For file extensions: check the Python tool's save/load logic to verify the actual file format used on disk — do not infer from the domain name.
```

### Action Taken

Applied: added two verification bullet points to `.github/agents/documenter.agent.md`.
