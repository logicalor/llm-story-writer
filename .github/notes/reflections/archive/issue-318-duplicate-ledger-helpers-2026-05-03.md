---
date: "2026-05-03"
issue: 318
pr: 330
category: agent
targets:
  - ".github/agents-copilot/coder.agent.md"
  - ".github/agents-openrouter/coder.agent.md"
severity: major
---

## Ledger helpers duplicated across `orchestrator.py` and `chapter_writer.py` — implementations already diverge

### Finding

PR #330 (issue #318) added `_work_item_done` and `_mark_work_item_done` to
`src/presentation/agents/chapter_writer.py` as new module-level functions, rather than importing
the identical helpers already defined in `src/presentation/orchestrator.py`. This was a conscious
Coder choice to avoid a potential circular import: `orchestrator.py` imports `ChapterWriterAgent`
from `chapter_writer.py`, so importing back from `orchestrator.py` would create a cycle.

However, the two implementations are not identical. The `orchestrator.py` version uses the
async `_write_savepoint()` wrapper:

```python
# orchestrator.py
async def _mark_work_item_done(state: PipelineState, phase: str, item_id: str) -> None:
    state.completed_work_items.setdefault(phase, [])
    if item_id not in state.completed_work_items[phase]:
        state.completed_work_items[phase].append(item_id)
    await _write_savepoint(state)                          # ← delegates to wrapper
```

The `chapter_writer.py` version calls `_atomic_write` directly:

```python
# chapter_writer.py
async def _mark_work_item_done(state: PipelineState, phase: str, item_id: str) -> None:
    state.completed_work_items.setdefault(phase, [])
    if item_id not in state.completed_work_items[phase]:
        state.completed_work_items[phase].append(item_id)
    _atomic_write(_savepoint_path(state.story_name), state.to_json())  # ← inline, not awaited
```

The `chapter_writer.py` version also omits the `await`, which is a functional difference: because
`_atomic_write` is synchronous, not awaiting it inside an `async def` is correct, but the two
modules now independently own the save semantics without a shared contract.

### Observation

The circular-import constraint is real and the Coder's decision to duplicate was a reasonable
pragmatic call given the constraint. However, the immediate divergence between the two copies
signals a maintenance risk:

1. **Future savepoint format changes** must be applied in two places. If `_write_savepoint` in
   `orchestrator.py` is updated (e.g., to include version metadata), `chapter_writer.py`'s inline
   equivalent silently lags behind.

2. **Additional pipeline phases** dispatched to separate agent classes will face the same choice
   and will likely create more copies. By issue #320 or #330+, there could be 3–4 independent
   implementations of the same function.

3. **`_savepoint_path` is duplicated too.** `chapter_writer.py` has its own copy of
   `_savepoint_path` pointing to the same path. If the savepoint location ever changes,
   all copies must be found and updated manually.

The root constraint (circular import) is solvable without duplication: a small shared module
in `src/presentation/` — e.g., `src/presentation/_ledger.py` — could hold `_savepoint_path`,
`_work_item_done`, and `_mark_work_item_done`. Both `orchestrator.py` and `chapter_writer.py`
import from `_ledger.py`, breaking the cycle. This is the same pattern used for `src/tools/_io.py`
(atomic write utilities) and `src/tools/_llm.py` (LLM helpers).

### Suggested Improvement

**For the Coder agent:** Add a guidance note:

> **When a helper needed by a sub-module already exists in a peer module that imports the
> sub-module (creating a potential circular import)** — do not duplicate the helper. Instead,
> extract the shared helper to a new `_<name>.py` private module in the same package (e.g.
> `src/presentation/_ledger.py`). Both the original module and the sub-module import from the
> new private module, breaking the import cycle without code duplication. This mirrors the
> `src/tools/_io.py` / `src/tools/_llm.py` extraction pattern. Duplicating the helper creates
> immediate implementation divergence within a single PR and accumulates further as future
> phases add their own copies.
>
> Concretely: `src/presentation/_ledger.py` is the appropriate home for `_savepoint_path`,
> `_work_item_done`, and `_mark_work_item_done` — all agents dispatched by the orchestrator
> that need ledger gating can import from this module without cycle risk.

**A follow-up issue should be opened** to:
1. Create `src/presentation/_ledger.py` with the three shared helpers
2. Replace the duplicates in `orchestrator.py` and `chapter_writer.py` with imports
3. Confirm no circular import introduced (run mypy)

### Action Taken

Applied: added "Shared helpers across presentation sub-modules — circular import avoidance"
guidance to Code Patterns in both coder.agent.md variants (copilot and openrouter).
Major structural follow-up (create `src/presentation/_ledger.py`) proposed for approval as a
separate issue — out of scope for the Reflection agent's direct edit scope.
