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

## Queue-backed "Bus" classes carry single-consumer semantics — name implies broadcast

### Finding

PR #170's `TokenBus` and `WikiContextBus` are named "bus" (a term strongly associated with pub-sub / broadcast messaging), but are backed by a single `asyncio.Queue` with competitive consumption semantics. Two of three reviewers flagged this as a semantic mismatch that could mislead future contributors into assuming multiple concurrent consumers are supported.

### Observation

There is no bug here — the single-consumer design is intentional for the current pipeline. However, the naming creates a long-term documentation risk: contributors adding a second consumer to a "bus" will observe silently dropped messages rather than a clear error, making the constraint invisible until production.

Given that this is an observation rather than a bug, no change to agent rules is required. The right mitigation is a doc comment in the source file itself (outside the scope of agent instruction changes). Recording here in case a future "Bus" implementation introduces the same pattern and the documentation concern recurs.

### Suggested Improvement

No agent or skill file change needed. The finding is recorded for future reference: when implementing an async channel named "Bus" or "Stream" that uses a single queue, document the single-consumer constraint in the class docstring.

### Action Taken

No action. Observation recorded for future reference.
