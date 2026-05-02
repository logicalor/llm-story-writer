# Task Breakdown: Granular Pipeline Checkpointing

> Implements [PRD](./prd.md)

**Date:** 2026-05-03

Tasks are ordered to land foundation infrastructure first, then convert each
phase one at a time. Each task is independently verifiable and small enough
for one Orchestrator dispatch. Phase conversions can run in any order after
Tasks 1–3 land.

## Tasks

### Task 1: Add `completed_work_items` to PipelineState + ledger helpers

**Type:** backend
**Estimated scope:** small
**Dependencies:** none

**Description:**
Add the `completed_work_items: dict[str, list[str]]` field to `PipelineState`
in `src/application/pipeline/handoffs.py`, including round-trip serialisation
in `to_dict` / `from_dict` (default to empty dict on legacy files). Add two
helpers in `src/presentation/orchestrator.py`:

- `_work_item_done(state, phase, item_id) -> bool`
- `async _mark_work_item_done(state, phase, item_id) -> None` — appends and
  writes the savepoint.

**Acceptance Criteria:**

- [ ] `PipelineState.completed_work_items` field added with default
- [ ] `to_dict` / `from_dict` round-trip preserves the dict
- [ ] Loading a legacy savepoint missing this field yields an empty dict
- [ ] `_work_item_done` and `_mark_work_item_done` exist and are typed
- [ ] Unit tests for round-trip and helpers

**Key Files:**

- `src/application/pipeline/handoffs.py` — add field + serialisation
- `src/presentation/orchestrator.py` — add helpers
- `tests/unit/test_pipeline_handoffs.py` — round-trip test
- `tests/unit/test_orchestrator.py` — helper tests

---

### Task 2: Make `_write_savepoint` atomic

**Type:** backend
**Estimated scope:** small
**Dependencies:** none (parallel with Task 1)

**Description:**
Replace the current `path.write_text(...)` in `_write_savepoint` with the
existing `_atomic_write` helper from `src/tools/_io.py` so SIGKILL during
save cannot truncate `pipeline_state.json`. Add a test that simulates a
write being interrupted (mock `os.replace` to fail after the temp file is
written) and confirms the previous savepoint is intact.

**Acceptance Criteria:**

- [ ] `_write_savepoint` uses `_atomic_write`
- [ ] Test confirms old file remains intact when write is interrupted
- [ ] No regression in normal save behaviour

**Key Files:**

- `src/presentation/orchestrator.py`
- `tests/unit/test_orchestrator.py`

---

### Task 3: Document the work-item-id convention

**Type:** backend (docs)
**Estimated scope:** small
**Dependencies:** Task 1

**Description:**
Add a short section to `docs/planning/granular-checkpointing/` explaining
the work-item-id grammar (`<phase>/<entity-slug>/<unit>`, `<phase>/<index>`,
etc.) so subsequent phase-conversion tasks pick consistent IDs. Include a
table listing the IDs each phase will use after conversion.

**Acceptance Criteria:**

- [ ] Convention doc committed
- [ ] Table covers all phases scheduled for conversion in tasks 4–10

**Key Files:**

- `docs/planning/granular-checkpointing/work-item-ids.md`

---

### Task 4: Convert Characters phase to ledger-driven loop

**Type:** backend
**Estimated scope:** medium
**Dependencies:** Tasks 1, 3

**Description:**
Refactor `_generate_character_sheets` in `src/presentation/orchestrator.py`
to consult and update the ledger:

- Cache the extracted name list as `characters/_names.json` and treat
  `characters/_names` as a work item; on resume, read the cached list
  rather than re-running `extract_names`.
- For each character, treat the base sheet, each chunk, the abridged, and
  the summary as separate ledger items. Skip any item already present.
- Read existing on-disk JSON when skipping so downstream items still see
  the correct `character_sheet` / `chunk_results` context.
- Use `_atomic_write` for every JSON write that backs a ledger entry.

**Acceptance Criteria:**

- [ ] Each LLM call inside the loop is gated by a `_work_item_done` check
- [ ] After each LLM call, `_atomic_write` then `_mark_work_item_done`
- [ ] Resume after killing mid-loop does not re-extract names, does not
      re-issue LLM calls for completed items, and produces an
      identical-on-disk result vs. an uninterrupted run
- [ ] Test simulates an interrupt at every LLM-call boundary

**Key Files:**

- `src/presentation/orchestrator.py` (`_generate_character_sheets`)
- `tests/unit/test_orchestrator.py`

---

### Task 5: Convert Settings phase to ledger-driven loop

**Type:** backend
**Estimated scope:** medium
**Dependencies:** Tasks 1, 3 (parallel with Task 4)

**Description:**
Apply the same pattern as Task 4 to `_generate_setting_sheets`. The chunk
list and naming convention differ but the structure is identical.

**Acceptance Criteria:**

- [ ] Same as Task 4 but for settings
- [ ] Test simulates an interrupt at every LLM-call boundary

**Key Files:**

- `src/presentation/orchestrator.py` (`_generate_setting_sheets`)
- `tests/unit/test_orchestrator.py`

---

### Task 6: Convert per-scene chapter drafting to ledger-driven loop

**Type:** backend
**Estimated scope:** medium
**Dependencies:** Tasks 1, 3

**Description:**
Refactor `ChapterWriterAgent._draft_via_scenes` in
`src/presentation/agents/chapter_writer.py` to:

- Persist each successful scene's prose to
  `stories/<story>/chapters/chapter_<N>/scene_<M>.md` via `_atomic_write`.
- Treat `chapter-N/scenes/decomposition` and `chapter-N/scene:<M>` as
  ledger items.
- On resume, read existing scene files back into the in-memory list before
  continuing the loop.
- Decomposition must also be resumable: cache the parsed scene list under
  `chapter_N_scenes.json` (already partially done) and key the ledger off
  that.

**Acceptance Criteria:**

- [ ] Killing the process between scenes resumes at the next undrafted scene
- [ ] Scene decomposition is not re-run on resume if already complete
- [ ] Test simulates interrupting after scenes 1, 2, …, N-1 and asserts
      scenes 1..k are loaded from disk on resume

**Key Files:**

- `src/presentation/agents/chapter_writer.py`
- `tests/unit/test_chapter_writer.py`

---

### Task 7: Convert per-chapter post-processing to ledger items

**Type:** backend
**Estimated scope:** medium
**Dependencies:** Tasks 1, 3

**Description:**
In the chapter loop in `_continue_pipeline`, treat each post-processing
step as its own ledger item under the chapter's phase:

- `chapter-N/draft`
- `chapter-N/consistency-check`
- `chapter-N/wiki-update`
- `chapter-N/sheet-evolution`
- `chapter-N/recap`
- `chapter-N/metadata` (only for chapter 1)

Each step skips itself if its ledger item is present. The chapter is only
marked complete after all six items are present.

**Acceptance Criteria:**

- [ ] Each post-processing step is gated by ledger
- [ ] Killing between draft and wiki-update resumes at wiki-update
- [ ] Killing between recap and metadata resumes at metadata
- [ ] Tests cover each interrupt point

**Key Files:**

- `src/presentation/orchestrator.py` (chapter-loop section)
- `tests/unit/test_orchestrator.py`

---

### Task 8: Convert Final-Edit phase to ledger-driven loop

**Type:** backend
**Estimated scope:** small
**Dependencies:** Tasks 1, 3

**Description:**
Refactor `FinalEditorAgent.run` (or the orchestrator block that drives it)
to:

- Treat `final-edit/chapter:<N>` as the ledger item per chapter.
- Persist the edited chapter content to disk before marking the item done
  (atomic write).
- On resume, load already-edited chapter content from disk into the result
  list and skip those LLM calls.

**Acceptance Criteria:**

- [ ] Per-chapter ledger entries
- [ ] Killing mid-pass resumes at the next unedited chapter
- [ ] Test simulates interrupt after every chapter

**Key Files:**

- `src/presentation/agents/final_editor.py`
- `src/presentation/orchestrator.py` (final-edit block)
- `tests/unit/test_final_editor_agent.py`

---

### Task 9: Convert Wiki-Bootstrap phase to ledger-driven loop

**Type:** backend
**Estimated scope:** small
**Dependencies:** Tasks 1, 3

**Description:**
In `bootstrap_wiki_from_story`, treat each entity bootstrap as a ledger
item (`wiki-bootstrap/<entity-slug>`). Skip entities already present in
the ledger; emit a status event per entity for TUI visibility (also
addresses the deferred "no progress visible" observability gap).

**Acceptance Criteria:**

- [ ] Per-entity ledger entries
- [ ] Killing mid-bootstrap resumes at the next un-bootstrapped entity
- [ ] Per-entity progress emitted on status bus

**Key Files:**

- `src/tools/wiki_bootstrap.py` (or wherever `bootstrap_wiki_from_story`
  lives — Planner did not pin the path)
- `tests/unit/test_wiki_bootstrap.py`

---

### Task 10: Convert Outline → Critique → Revision to ledger items

**Type:** backend
**Estimated scope:** small
**Dependencies:** Tasks 1, 3

**Description:**
Treat the outline draft, critique, and revision as three ledger items
under the `outline` phase. The current code persists the outline to
`PipelineState.outline_result` and the critic summary to
`state.critic_summary`; both already round-trip via savepoint, so the
ledger items only need to gate the LLM calls.

**Acceptance Criteria:**

- [ ] Each of the three steps is gated
- [ ] Killing between draft and critique resumes at critique
- [ ] Killing between critique and revision resumes at revision
- [ ] Test covers both interrupt points

**Key Files:**

- `src/presentation/orchestrator.py` (outline section)
- `tests/unit/test_orchestrator.py`

---

### Task 11: TUI status reflects pending sub-step on resume

**Type:** frontend
**Estimated scope:** small
**Dependencies:** Tasks 4–10 (any subset)

**Description:**
On resume, emit a status event listing the next pending work item per
phase so the TUI Activity panel shows the user where the run will pick
up. Helps the user predict cost.

**Acceptance Criteria:**

- [ ] On resume, the TUI prints a "Resuming at: <phase>/<item>" banner
- [ ] If the work-item ledger is empty (legacy savepoint), the message
      is suppressed and behaviour matches today

**Key Files:**

- `src/presentation/orchestrator.py` (resume entry)
- `src/presentation/tui/app.py` (no behaviour change; sanity check)
- `tests/unit/test_tui.py`

---

### Task 12: End-to-end interrupt + resume integration test

**Type:** backend (integration)
**Estimated scope:** medium
**Dependencies:** all preceding tasks

**Description:**
Add an integration test under `tests/integration/` that runs the pipeline
against a recorded LLM fixture, kills it deterministically at a series of
sub-step boundaries, resumes, and asserts the final story output is
byte-identical to a baseline uninterrupted run, with a recorded count of
LLM calls that exactly matches expectation (no duplicate calls).

**Acceptance Criteria:**

- [ ] Test exists under `tests/integration/test_resume_granularity.py`
- [ ] Asserts byte-identical output across interrupted vs. uninterrupted
      runs
- [ ] Asserts the LLM fixture is called the exact expected number of
      times across the full interrupt-resume sequence

**Key Files:**

- `tests/integration/test_resume_granularity.py`
- Fixture under `tests/fixtures/`
