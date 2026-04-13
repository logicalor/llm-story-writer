---
date: "2026-04-13"
issue: 6
pr: 35
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: active
---

## Boundary validation must check element types, not just container types

### Finding

During issue #6 (Build character-mgr Tool), the `extract-names` operation validated that the LLM response was a list (`isinstance(result, list)`) but did not verify each element was a string. All three reviewers caught this unanimously (U-W-01).

The general pattern: system boundary validation that checks only the container type (list, dict) but not element types (str, int) is incomplete. LLM output is untrusted — it may return `[1, null, {"name": "Alice"}]` when `["Alice", "Bob"]` is expected.

### Observation

Coder Rule 9 covers subprocess security (CWE-78) and path traversal (CWE-22) but does not address general input validation depth at system boundaries. The project's `copilot-instructions.md` says "Only validate at system boundaries" — this is correct but the Coder needs guidance on *how deep* that validation should go.

This is a clarification/expansion of the existing Rule 9, not a new workflow step.

### Suggested Improvement

Expand Coder Rule 9's header from "Security: subprocess and path handling" to "Security: subprocess, path, and input validation" and add a third sub-bullet:

```markdown
   - **Boundary validation depth:** When validating data at system boundaries (LLM output, file reads, API responses), validate both the container type *and* the element types. E.g., checking `isinstance(result, list)` is insufficient — also verify each element matches the expected type (e.g., `all(isinstance(el, str) for el in result)`).
```

### Action Taken

Applied: expanded Coder Rule 9 with boundary validation depth sub-bullet.
