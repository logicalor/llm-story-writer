---
date: "2026-04-17"
issue: 27
pr: 87
category: instruction
targets:
  - ".github/notes/patterns.md"
severity: minor
status: archived
---

## Session-scoped fixture + LLM subprocess pattern for long-running E2E tests

### Finding

During issue #27 (Task 25: End-to-End Integration Test with Wiki), the test suite used a session-scoped pytest fixture (`pipeline_result`) that ran the full story generation pipeline once and shared the result with all 12 test functions. This design allowed a long-running LLM pipeline (multiple tool invocations, wiki updates, ChromaDB operations) to be tested with 12 assertions without re-running the pipeline per test.

### Observation

This is a valid and efficient pattern for E2E integration tests where the subject-under-test is an LLM-driven pipeline that would be prohibitively slow to re-run for each assertion. The key design attributes:

1. **Session-scoped fixture** — `@pytest.fixture(scope="session")` runs the pipeline once; all test functions receive the pre-computed `pipeline_result` dict.
2. **Pre-computed results** — the fixture captures all outputs (chapters, wiki pages, savepoints, ChromaDB entries) into a dict. Test functions assert against this dict.
3. **Isolation via assertions** — each test function checks one aspect of the result (e.g., chapter text non-empty, wiki page fields present, savepoint created). Tests do not re-invoke the LLM.
4. **Failure semantics** — if the pipeline fixture itself fails, all 12 tests are marked as ERROR, not FAIL. This clearly signals "pipeline broke" vs. "assertion failed."

This pattern is appropriate when:

- The operation under test is slow (> 30s), expensive (LLM inference), or stateful (filesystem writes, DB inserts)
- Multiple distinct properties of the same output need to be verified
- Re-running the operation per-test would make the suite impractical

It is **not** appropriate for unit tests of pure functions, or when test isolation between tests is required (each test needs a fresh state).

### Suggested Improvement

When `.github/notes/patterns.md` is created (per issue #7 reflection), add this as a testing pattern entry:

```markdown
### Session-Scoped Fixture for Long-Running LLM Pipeline Tests

When testing a full LLM pipeline (tool calls, file writes, DB operations), use a session-scoped
fixture to run the pipeline once and share results across all assertions.

```python
@pytest.fixture(scope="session")
def pipeline_result():
    """Run the full pipeline once; all tests share pre-computed results."""
    result = {}
    # ... invoke the pipeline ...
    result["chapter_text"] = ...
    result["wiki_pages"] = ...
    return result

def test_chapter_generated(pipeline_result):
    assert pipeline_result["chapter_text"]

def test_wiki_updated(pipeline_result):
    assert "character" in pipeline_result["wiki_pages"]
```

Failure semantics: fixture failure → ERROR (pipeline broken); assertion failure → FAIL (output wrong).
```

### Action Taken

Deferred — target file (`patterns.md`) does not exist yet. Recorded for inclusion when the conventions collection is created (issue #7 dependency).
