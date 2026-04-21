# Dispatch Failure Recovery

> Retry protocol for agent dispatch failures. **Include in any agent that dispatches sub-agents.**

---

When dispatching to any agent, the following errors are retryable:

- "Response contained no choices"
- Timeout failures (see "Timeout with Possible Completion" below before retrying)
- Rate limit errors

**Retry protocol:**

1. Wait 2 seconds, then retry the dispatch
2. If still fails, wait 4 seconds, then retry
3. If still fails, wait 8 seconds, then retry
4. After 3 failed attempts, post a PR comment and notify the user — do not continue

When retrying, include the same context but add: "This is retry attempt N of 3."

---

## Timeout with Possible Completion

A timeout failure may mean the agent completed its work but ran out of time to return a report. Before retrying:

1. **Check for side effects** — look for file changes, commits, or other expected outputs
2. **If work appears completed** — treat as Empty Response (section below): proceed without retry
3. **If no side effects found** — apply the standard retry protocol above

Retrying a dispatch where work was already completed risks double-writes, duplicate commits, or conflicted state.

---

## Empty Response Handling

If an agent returns successfully but with an empty or "no response" message:

1. **Check if the agent's expected work was completed** — look for file changes, commits, or other side effects
2. **If work was completed** — proceed; the agent finished but couldn't formulate a return message
3. **If work was NOT completed** — retry the dispatch (counts against retry limit above)
4. **Log the empty response pattern** for reflection in the task summary

If an agent returns successfully but explicitly states it made no changes (or returns a "no response" message with no side effects), and the work is not complete:
- Retry the dispatch (counts against retry limit)
- If retry fails or is not warranted (e.g., agent explicitly declines), proceed with direct Orchestrator implementation only for trivial changes
- For non-trivial changes, escalate to the user rather than implementing complex logic directly

This pattern occurs occasionally with some models that complete work but return empty responses.
