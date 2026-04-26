---
date: "2026-04-26"
issue: 187
pr: 200
category: agent
targets:
  - ".github/agents/test-writer.agent.md"
severity: minor
status: archived
---

## Patch local imports at the source module, not at asyncio.run

### Finding

During issue #187/PR #200, the `TestCmdRun` test suite patched `asyncio.run` instead of patching the imported `run_pipeline` function at the calling module's namespace. The `cmd_run` function used an inline local import (`from module import fn` inside the function body), so the patch needed to target the source module's attribute — not `asyncio.run`, which is a generic coroutine dispatcher. This caused `RuntimeWarning: coroutine '...' was never awaited` because `asyncio.run` was bypassed by the mock before it could await the coroutine.

### Observation

This is a specialised variant of the standard "patch at the consumer's namespace" rule. When a function uses an **inline local import** (`from module import fn` inside the function body), the import resolves at call time, not at module-load time. Patching `asyncio.run` to intercept a specific coroutine call is incorrect: the real `asyncio.run` is replicated for every coroutine, but patching removes the event loop entry entirely, leaving unawaited coroutines. The correct target is the imported name at its source module (`patch("src.module.run_pipeline", new=AsyncMock(...))`).

### Suggested Improvement

Add a bullet to the **"Textual `@work(thread=True)` apps"** paragraph in `test-writer.agent.md`, clarifying the correct patch target for functions using inline local imports.

### Action Taken

Applied: Added a note to the `test-writer.agent.md` Textual worker section clarifying that when testing functions with inline local imports, the patch target must be the source module's attribute (e.g., `patch("src.tools.pipeline.run_pipeline", new=AsyncMock(...))`) — not `asyncio.run`. Patching `asyncio.run` generically bypasses the event loop without awaiting the coroutine, producing `RuntimeWarning: coroutine '...' was never awaited`.
