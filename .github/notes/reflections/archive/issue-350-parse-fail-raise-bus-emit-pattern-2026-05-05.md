---
date: "2026-05-05"
issue: 350
pr: 365
category: agent
targets:
  - ".github/agents-copilot/coder.agent.md"
  - ".github/agents-openrouter/coder.agent.md"
  - ".opencode/agents/coder.md"
severity: minor
---

## LLM parse failure in orchestrator helpers — raise ValueError + bus emit pattern

### Finding

`_coerce_event_list` in `orchestrator.py` previously caught `JSONDecodeError` and returned `[]` silently. This caused `_sync_recap_events_to_wiki` to exit with `{created: 0, updated: 0}` with no indication of the failure — confirmed across all four chapters of `breaking-amy`. PR #365 fixed this by:
1. Having `_coerce_event_list` raise `ValueError("unparseable event list: …")` on parse failure
2. Having the call site catch `ValueError` and emit `"[Recap] event parse failed: …\n"` to the status bus

### Observation

This is a general pattern for orchestrator helper functions that parse LLM output: the helper function raises, the orchestrator call site emits the error to the bus. No existing guidance covered this pattern — the related `"LLM-response parse-error paths"` guidance in test-writer covers tools that exit with non-zero code, which is a different scenario. Without guidance, future helpers may follow the old silent-return antipattern, making failures invisible.

### Suggested Improvement

Add a new code pattern bullet to all three coder agent files:

> **LLM parse failure in orchestrator helpers — raise + bus emit:** When an orchestrator helper function parses LLM output (e.g. `_coerce_event_list`), raise `ValueError` on parse failure rather than returning a silent empty default. The call site should wrap in `try/except ValueError` and emit the error to the status bus. Pattern: `except ValueError as exc: await bus.emit(f"[Recap] event parse failed: {exc}\n")`. This ensures failures surface through the bus observability layer rather than producing silent zero-output results that are invisible in logs and tests. (Source: issue #350, PR #365.)

### Action Taken

Applied: added the pattern bullet to `.github/agents-copilot/coder.agent.md`, `.github/agents-openrouter/coder.agent.md`, and `.opencode/agents/coder.md` after the existing LLM fenced JSON extraction bullet (or equivalent section).
