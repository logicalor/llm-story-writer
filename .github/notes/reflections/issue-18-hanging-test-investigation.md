---
date: "2026-04-15"
issue: 18
pr: 64
category: instruction
targets:
  - ".github/notes/deferred.md"
severity: minor
status: active
---

## pytest tests/ hangs after ~176 tests — tests/unit/ runs clean

### Finding

During issue #18 (Build Outline Planner Subagent), running `pytest tests/` caused the test suite to hang after approximately 176 tests. Running `pytest tests/unit/` completes cleanly with 241 tests passed. The hanging test is somewhere outside `tests/unit/` — likely in `tests/integration/` or the root-level `test_*.py` files.

This was not related to PR #64's changes and appears to be a pre-existing condition.

### Observation

The root-level `test_*.py` files (e.g., `test_rag_integration.py`, `test_progressive_story_generation.py`, `test_multistep_conversation.py`) are legacy test files that may attempt network calls (LLM inference, RAG queries) or wait for interactive input. These are likely the source of the hang — they may block on a connection timeout or stdin read.

The project's test convention (`tests/unit/`, `tests/integration/`) suggests these root-level test files are not part of the standard test suite. `pytest tests/unit/` is the correct command for CI and routine verification. However, the hanging behaviour should be investigated to either fix the blocking tests or exclude them from the default `pytest tests/` collection.

### Suggested Improvement

Add an entry to `.github/notes/deferred.md` for investigation:

```markdown
## Investigate hanging test in `pytest tests/`

**Date:** 2026-04-15
**Source:** Reflection — issue #18

Running `pytest tests/` hangs after ~176 tests; `pytest tests/unit/` completes cleanly (241 passed). The hang is likely caused by root-level `test_*.py` files that attempt network calls or wait for input. Investigate and either fix (add timeouts/mocks) or exclude from default collection (add to `pyproject.toml` `testpaths` or a `conftest.py` collect_ignore).
```

### Action Taken

Applied: added entry to `.github/notes/deferred.md`.
