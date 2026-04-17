### Review Summary

The PR introduces retry logic for LLM text generation in integration tests using a new `_generate_with_retry` helper function. The changes are focused, well-tested, and maintain clean separation of concerns. A minor edge case regarding zero or negative `max_attempts` could result in an unhelpful error message, but it does not affect normal execution paths.

**Files Reviewed:** 2
**Findings:** 0 Critical, 0 Warning, 1 Suggestion

### Findings

#### Suggestions

[S-01] Handle zero or negative max_attempts gracefully
Category: Correctness
Severity: Suggestion
File: tests/integration/test_e2e_opencode.py
Lines: 123-132
Description: If `_generate_with_retry` is called with `max_attempts <= 0`, the `for` loop body will never execute, leading to a `RuntimeError("unreachable")`. While this isn't expected in normal usage, it would be safer to validate the input or initialize `last_err` with a more descriptive error such as `ValueError("max_attempts must be >= 1")`.
Suggestion: Add an early return or assertion for `max_attempts`:
```python
def _generate_with_retry(prompt: str, max_attempts: int = 3) -> str:
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    # ...
```

### Overall Assessment

The code is ready for merge. The implementation effectively addresses transient LLM failures in tests, and unit testing for the backoff schedule and retry behavior is solid. The single suggestion is defensive programming for an edge case and does not block merging.
