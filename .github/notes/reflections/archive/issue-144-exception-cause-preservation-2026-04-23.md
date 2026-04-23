---
date: "2026-04-23"
issue: 144
pr: 145
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## Exception cause preservation when refactoring helpers that wrap exceptions

### Finding

PR #145 extracted `run_batch()` from `cmd_batch()` in `src/tools/wiki_update.py`. The new helper's exception path performs rollback then re-raises:

```python
raise RuntimeError(json.dumps({"rollback": rollback})) from None
```

Two reviewers (Claude, GPT) flagged this as a Warning. `from None` discards the entire exception chain, and the JSON-only payload omits the original message. The downstream caller (`wiki_extract.py` `_error()`) prints `'{"rollback": "full"}'` as its message field — a JSON-in-JSON artefact with the actual cause (e.g. `"wiki not initialised"`, `"duplicate slug"`, `"invalid page type"`) entirely lost. This is a regression from the pre-refactor `cmd_batch()` path, which surfaced the original exception text alongside rollback state.

### Observation

This is a new defect class for the Coder. Existing rules cover:

- "Proper error handling — no swallowed exceptions" (review-checklist Data Access)
- Boundary validation depth (Coder Rule 9)

Neither rule addresses the specific anti-pattern of `raise NewError(...) from None` in **refactored helpers** that previously surfaced the underlying cause. The pattern is seductive during refactor: the helper wants to return structured state (rollback status), so the author wraps it in a single new exception type, and `from None` "cleans up" the traceback. The cost — losing the original cause — is invisible in unit tests that exercise only the happy path or assert the wrapper type.

The correct pattern is `raise NewError(...) from exc` (preserves `__cause__` and the chained traceback) and structuring the new error payload to include the original message string explicitly so non-Python callers (TypeScript wrappers, JSON-printing CLI scripts) can surface it.

### Suggested Improvement

Add a "Wrapping exceptions during refactor" entry to the Coder agent's Code Patterns section covering `raise ... from exc` over `raise ... from None`, and recommending that structured error payloads include `"cause": str(exc)` when the original message is being JSON-encoded for a non-Python consumer.

### Action Taken

Applied: added "Exception wrapping during refactor" pattern note to the Code Patterns section of `.github/agents/coder.agent.md`, citing PR #145.
