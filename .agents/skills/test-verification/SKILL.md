---
name: test-verification
description: Use when writing, updating, or evaluating tests for this repository, especially after implementation changes or when validating CLI/tool behavior.
---

# Test Verification

Tests verify implemented behavior. They should be meaningful, isolated, and aligned with existing patterns.

## Workflow

1. Load `project-memory` and query the `tests` collection.
2. Read nearby tests before adding new ones.
3. Prefer extending existing test files over creating isolated new files.
4. Write focused tests for the changed behavior.
5. Run the smallest useful test command first, then broader checks as risk increases.

## Assertions

- Assert specific expected values, not only non-empty results.
- Keep expected constants independent from production constants when pinning contract values.
- For argparse validation, assert `returncode == 2` and useful stderr.
- For LLM JSON parsing, cover invalid JSON, valid non-dict JSON, null sections, and mixed list items when relevant.
- For disk-writing code, patch storage roots and avoid real story data.

## Handoff

Report test files changed, test cases added, commands run, and any pre-existing failures.
