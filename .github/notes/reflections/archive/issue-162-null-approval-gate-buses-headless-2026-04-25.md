---
date: "2026-04-25"
issue: 162
pr: 172
category: instruction
targets:
  - ".github/notes/gotchas.md"
severity: minor
status: archived
---

## Canonical headless pipeline invocation: `NullApprovalGate` + `TokenStreamBus` + `WikiContextBus`

### Finding

PR #172 introduced the first Python-native CLI entry point invoking `run_pipeline()` and
`resume_pipeline()` in headless (non-interactive) mode. The correct invocation pattern requires
three collaborating objects — `NullApprovalGate`, `TokenStreamBus`, and `WikiContextBus` — that
are not documented anywhere in the agent knowledge base.

```python
gate = NullApprovalGate()
bus = TokenStreamBus()
wiki_bus = WikiContextBus()
asyncio.run(run_pipeline(story, gate, bus, wiki_bus))
```

`NullApprovalGate` auto-approves all quality gates. `TokenStreamBus` and `WikiContextBus` are
unbounded asyncio queues; safe to create and discard in headless mode (closed in the pipeline's
`finally` block).

### Observation

Any future CLI subcommand, batch script, or CI runner that invokes `run_pipeline()` needs this
pattern. Without documentation, a new implementer is likely to either: (a) fabricate a different
pattern that blocks on an interactive gate, or (b) omit the buses entirely and trigger
`AttributeError` when the pipeline calls `bus.emit()`.

### Suggested Improvement

Add gotcha entry #021 to `.github/notes/gotchas.md` under `## CLI / Entry Points` documenting
the canonical headless invocation pattern.

### Action Taken

Applied: added gotcha entry #021 (`gotcha-null-approval-gate-headless-pipeline-021`) to
`.github/notes/gotchas.md` under `## CLI / Entry Points`.
