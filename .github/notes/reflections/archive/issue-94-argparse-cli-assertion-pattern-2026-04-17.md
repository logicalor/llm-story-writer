---
date: "2026-04-17"
issue: 94
pr: 95
category: agent
targets:
  - ".github/agents/test-writer.agent.md"
severity: minor
status: archived
---

## Argparse CLI validation tests require `returncode == 2` + stderr check

### Finding

Issue #94 (PR #95) added CLI validation-error path tests for `wiki_read.py`. One test (`test_invalid_operation`) initially only checked `returncode != 0`. The synthesized review found this unanimously weak — a runtime exception or any non-zero exit also satisfies `returncode != 0`, so the assertion does not distinguish an argparse validation error from a crash.

The correct pattern: assert `returncode == 2` (argparse's standard exit code for argument parsing failures) **and** check that `stderr` contains a meaningful error fragment such as `"invalid choice"` or `"invalid-value"`.

### Observation

This is the first PR where the review caught a weak CLI assertion in a test-only PR. The full review cycle added genuine value even though no production code changed. The test in question was strengthened before merge — correct outcome, but the Test Writer should produce the correct assertion pattern without relying on the review cycle to catch it.

Argparse exits with code 2 for all usage/validation errors (wrong type, unrecognised argument, invalid choice, missing required argument). This is stable, well-documented behaviour. Adding it as named guidance in the Test Writer prevents this class of weak assertion from recurring.

### Suggested Improvement

Add a "CLI validation assertions" named block to the Test Writer agent's **Write Tests** section, immediately after the existing "Collection assertions" block:

```markdown
**CLI validation assertions (argparse tools):** When testing CLI tools that use `argparse`, validation-error tests must assert both `returncode == 2` (argparse's standard exit code for argument parsing failures) and that `stderr` contains a meaningful error fragment such as `"invalid choice"` or `"required"`. Checking only `returncode != 0` is insufficient — it does not distinguish argparse validation errors from runtime exceptions or other error types.
```

### Action Taken

Applied: added "CLI validation assertions" block to `.github/agents/test-writer.agent.md` after the "Collection assertions" block.
