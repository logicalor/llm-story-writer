---
date: "2026-04-26"
issue: 188
pr: 201
category: agent
targets:
  - ".github/agents/documenter.agent.md"
severity: minor
status: archived
---

## ADR retirement plans must document test functions that consume production files as disk artifacts

### Finding

ADR 008 listed `critique_service.py` for deletion without noting that `tests/unit/test_critique_service.py` contains `test_critique_service_has_dict_any_imports()` (lines 52–71), which opens `critique_service.py` by path via `ast.parse()`. Deleting the production file without removing this test function produces a silent `FileNotFoundError` at test runtime — a breakage that is invisible at review time unless the reviewer specifically audits for filesystem-coupled tests.

The ADR retirement plan was otherwise well-constructed and all other inventory claims were accurate. The gap is specific to the "Files to delete" section not accounting for test consumers that couple to production files as filesystem artefacts rather than through Python imports.

### Observation

ADR retirement plans commonly enumerate production files to delete and note which callers must be updated. They do not routinely audit whether any test functions _read_ those production files by path — a distinct category of dependency that cannot be detected by tracing Python imports. A function like `ast.parse(open("src/application/services/critique_service.py").read())` creates a hard filesystem dependency that survives import-graph analysis.

This pattern is most common in structural tests that verify the internal composition of a source file (import presence, class membership, annotation coverage) using AST introspection. It is possible for such tests to exist without their production file appearing in the test's `import` statements, making them invisible to standard dependency analysis.

When a cleanup issue is derived from the ADR and executes the deletion, the test suite breaks immediately. The fix (delete only the affected function, preserve the rest of the file) is non-obvious unless the ADR or cleanup issue explicitly records the co-deletion requirement.

### Suggested Improvement

In the Documenter agent's Step 3 "Write Documentation" verification checks, add a bullet under the "New ADR" guidance specifying that retirement plans listing files to delete must include proof of test audit:

> "For ADRs with a retirement plan that lists files to delete: run `grep -rn 'ast.parse\|open(' tests/` filtered for paths containing the service name, and check for any test function that reads the file from disk by path. If found, document the co-deletion requirement explicitly — naming the test function, test file, and remaining tests that must be preserved — either in the ADR's 'Files to delete' section or in the body of the associated cleanup issue."

### Action Taken

Applied: added "Disk-artifact test audit" verification bullet to Step 3 in `documenter.agent.md`, immediately after the existing "behavioral descriptions" bullet in the verification checks list.
