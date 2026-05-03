# ADR 010: Work-Item Ledger for Granular Pipeline Checkpointing

**Date:** 2026-05-03
**Status:** Accepted

## Context

`pipeline_state.json` records `completed_phases` at top-level phase
boundaries. Inside a phase, work happens in loops over expensive LLM calls
(N characters × 9 calls each, M settings × 7 calls each, K scenes per
chapter, per-chapter wiki/recap/eval/edit passes). Interrupting in the
middle of any loop discards the loop's progress on resume, even when
intermediate artefacts were already written to disk, because nothing in
state tells the loop what is already done.

We need a checkpoint unit smaller than a phase but stable across runs and
cheap to persist. Three options were considered:

1. **Per-phase event sourcing.** Append events to a log; replay to recover
   state. Powerful but requires every phase to define event schemas and
   reducers. High implementation cost; overkill for our needs.
2. **On-disk artefact discovery.** Have each loop check whether its output
   file already exists and skip if so. Simple but brittle: the file's
   existence does not prove completeness (a partial JSON write looks the
   same as a complete one), and some artefacts are not 1:1 with LLM calls
   (chunks live inside a single character JSON).
3. **Explicit work-item ledger inside `PipelineState`.** Each loop records
   the IDs of items it has finished. The ledger is the single source of
   truth for "is this LLM call already done?".

## Decision

Adopt option 3: a `completed_work_items: dict[str, list[str]]` field on
`PipelineState`, populated by an `_mark_work_item_done` helper that
atomically writes the savepoint after appending the ID.

Work-item IDs are deterministic strings of the form
`<phase>/<entity-slug>/<unit>`, `<phase>/<index>`, or
`<phase>/<entity-slug>` depending on the loop. The orchestrator owns the
naming convention; agents just call the helpers.

The ordering invariant is **artefact write → ledger update**, both atomic.
A crash between them re-runs the LLM call (correct, idempotent at the
artefact level). A crash between ledger update and next item is also
correct: the ledger reflects what is on disk.

## Consequences

### Positive

- Resuming a kill never wastes an LLM call whose output was already
  persisted — direct user-facing cost saving.
- Single helper API means new phases get granular resume by default.
- Ledger is plain JSON, inspectable and hand-editable for debugging.
- Backward compatible: legacy savepoints load with empty ledger and behave
  as before for one run, then populate going forward.

### Negative

- Each LLM call now triggers two disk writes (artefact + savepoint). Cost
  is one additional ~1–10 KB write per LLM call; LLM latency dwarfs this.
- Phase code becomes slightly more complex: gate, do work, persist, mark
  done, plus a "load existing artefact when skipping" branch for steps
  whose output feeds later steps.
- Work-item ID strings are not type-checked at compile time; a typo
  silently disables resume for that item. Mitigation: per-phase constants
  and unit tests.

### Neutral

- The phase list does not change; `completed_phases` continues to mark
  end-of-phase. The ledger sits underneath it.
- Integration test costs grow because we test interrupt-resume at every
  sub-step boundary; mitigated by replay-from-fixture rather than live
  LLM calls.

## Implementation Status

ADR 010 is now implemented across the planned task set.

- Issue #318 / PR #330 completed Tasks 4 through 6 for characters, settings, and per-scene chapter drafting.
- Issue #320 / PR #332 completed Tasks 7 through 11 for per-chapter post-processing, final edit, wiki bootstrap, outline draft and critique ledger items, and the TUI resume banner.

The active runtime now records ledger entries for outline draft and critique, character and setting sheet generation, wiki bootstrap entities, scene decomposition and per-scene chapter drafting, per-chapter post-processing sub-steps, and per-chapter final edit output.
