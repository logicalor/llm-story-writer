---
date: "2026-04-24"
issue: 160
pr: 170
category: instruction
targets:
  - ".github/notes/gotchas.md"
severity: minor
status: active
---

## Asyncio `Future` lazy-init: `resolve()` before `await_decision()` is a no-op → deadlock

### Finding

PR #170's `ApprovalGate` created its `asyncio.Future` lazily inside `await_decision()`. All three reviewers unanimously flagged that calling `resolve()` before `await_decision()` was a no-op: no Future existed yet, so the resolution was silently discarded. When `await_decision()` was later called, it created a fresh Future and waited forever — a deadlock with no error signal.

### Observation

Lazy `asyncio.Future` creation inside an `await` method is a common pattern for "don't create the Future until someone is waiting". However, it immediately creates a race: any caller that reasonably calls `resolve()` first receives no error and observes no feedback; the waiter then blocks forever. The fix is to buffer the pending result in `__init__` and return it immediately if already resolved when `await_decision()` is first called.

This pattern affects any two-party coordination primitive (approval gate, one-shot latch, promise-style object) where resolve/settle can occur before the waiter registers.

### Suggested Improvement

Add gotcha entry #015 to `.github/notes/gotchas.md` under `## Async / Threading` documenting the lazy-Future deadlock and the buffered-pending-result fix pattern.

### Action Taken

Applied: added gotcha #015 (`gotcha-asyncio-future-lazy-init-deadlock-015`) to `.github/notes/gotchas.md`.
