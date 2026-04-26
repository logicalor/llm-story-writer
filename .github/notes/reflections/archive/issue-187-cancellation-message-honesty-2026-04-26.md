---
date: "2026-04-26"
issue: 187
pr: 200
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## User-facing cancellation messages must reflect actual thread lifecycle for @work(thread=True)

### Finding

During issue #187/PR #200, a "Pipeline cancelled" status message was displayed after a Ctrl+C / `worker.cancel()` call on a Textual `@work(thread=True)` worker. However, Textual's threaded workers do not terminate immediately on `cancel()` — they run to the end of their current phase and stop at the next cancellation checkpoint. The message was therefore factually incorrect at the moment of display.

### Observation

Textual `@work(thread=True)` workers are OS threads. `worker.cancel()` sets a cancellation flag that is only checked at explicit checkpoints (or on the next iteration). Unlike asyncio tasks, there is no cooperative `CancelledError` propagation across yield points. Describing the pipeline as "cancelled" before the thread has exited implies immediate termination, raising user expectations the system cannot meet. The accurate message is something like "Cancellation requested. Pipeline will finish its current phase before stopping."

This pattern generalises to any non-cooperative concurrency model (threads, processes) where cancellation is advisory rather than preemptive.

### Suggested Improvement

Add a note to `coder.agent.md` in the "Framework integration verification" section (Rule 10) or under a user-facing message honesty guideline: when writing cancellation feedback for `@work(thread=True)` workers, do not state "cancelled" — the thread is still running until its current phase completes. Use "cancellation requested" or "will stop after current step" instead.

### Action Taken

Applied: Added a sub-bullet to Rule 10's Textual worker / threading guidance in `coder.agent.md`.
