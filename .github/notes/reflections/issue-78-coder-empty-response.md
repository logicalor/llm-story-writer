---
date: "2026-04-16"
issue: 78
pr: 81
category: agent
targets:
  - ".github/agents/orchestrator-v3.agent.md"
  - ".github/agents/_shared/dispatch-retry.md"
severity: minor
status: active
---

## Coder returned empty — Orchestrator implemented directly as fallback

### Finding

During issue #78 (Exclude legacy/ from repo-wide lint), the Coder subagent was dispatched but returned without making any changes (empty response, no file modifications). The Orchestrator then implemented the changes directly — creating pyproject.toml with `legacy/` excluded from ruff, removing an unused `chapter_list` assignment in outline_service.py, and replacing two bare `except:` with `except Exception:` in chapter_generator.py.

### Observation

This is a new subagent failure pattern distinct from the dispatch-retry.md empty response handling. The Coder returned "successfully" (no error, no retry triggered) but with no content and no side effects. The dispatch-retry.md empty response section assumes the agent will either complete work with side effects OR return empty — but doesn't cover the case where the agent explicitly states it made no changes.

The Orchestrator correctly fell back to direct implementation per mode instructions ("If minor: apply the improvement immediately"). The work was straightforward (3 small changes), so the direct implementation was viable. For more complex work, this fallback would not be adequate — a retry or different agent would be needed.

### Suggested Improvement

Add a clause to dispatch-retry.md "Empty Response Handling" section:

> If an agent returns successfully but explicitly states it made no changes (or returns a "no response" message with no side effects), and the work is not complete:
> - Retry the dispatch (counts against retry limit)
> - If retry fails or is not warranted (e.g., agent explicitly declines), proceed with direct Orchestrator implementation only for trivial changes
> - For non-trivial changes, escalate to the user rather than implementing complex logic directly

This distinguishes "agent finished but couldn't formulate return message" (has side effects, proceed) from "agent explicitly made no changes" (work incomplete, needs retry or escalation).

### Action Taken

Applied: Added the above clause to dispatch-retry.md Empty Response Handling section.
