# PRD: Granular Pipeline Checkpointing

> Persist progress at every meaningful sub-step so a story run can be interrupted and resumed without re-doing finished LLM work.

**Date:** 2026-05-03
**Author:** Planner agent
**Status:** Draft

## Problem Statement

The pipeline currently checkpoints only at top-level phase boundaries (`init`,
`story-foundation`, `outline`, `metadata-outline`, `narrative-arc`,
`characters`, `settings`, `wiki-bootstrap`, `chapter-loop`, `final-edit`,
`metadata-final`, `assembly`). Inside any one of those phases, work happens in
loops over expensive LLM calls — character sheets per character × per chunk,
setting sheets per location × per chunk, scene drafts per scene per chapter,
recap and sheet evolution per chapter, final-editor passes per chapter — but
none of those intermediate outputs cause `pipeline_state.json` to advance.

Concretely:

- **Characters phase:** for each of N characters the orchestrator runs ~9 LLM
  calls (sheet + 7 chunks + abridged + summary). If the user stops after 4
  characters, the partial JSON for those 4 is written to disk but the phase is
  not marked complete, so on resume `_generate_character_sheets` re-extracts
  the full name list and starts over from character 1, regenerating every
  sheet. The on-disk JSON is overwritten with new content.
- **Settings phase:** identical pattern (~7 chunks per setting).
- **Chapter loop, scene-by-scene drafting:** scene definitions are persisted
  to `chapter_N_scenes.json` but per-scene prose is held in a list in memory.
  Stopping after scene 4 of 7 means scenes 1–4 are lost on resume; the chapter
  starts decomposition again from the synopsis.
- **Final-edit phase:** edits N chapters in a loop with no per-chapter
  checkpoint. Stopping mid-pass discards everything edited so far.
- **Per-chapter post-processing:** wiki update, sheet evolution, recap, and
  metadata-chapter-1 each run in their own try/except block but are not
  individually resumable — if the run dies between them, on resume they all
  run again.
- **Outline phase:** the outline LLM call itself is a single shot, but
  outline → critique → revision is a loop with no resumable midpoint.

This is the same class of bug as the wiki-bootstrap silent-completion case
fixed earlier in this session: when the unit of resumable work is coarser
than the unit of LLM work, an interruption costs the user real money and
time. The user's reported case is character generation: stopping mid-phase
restarts the entire phase.

## Goals

1. Resume from the **last completed sub-step** — never re-run an LLM call
   whose output has already been persisted.
2. Do this for **every** phase that contains a loop over LLM calls, not just
   the chapter loop.
3. Make checkpointing **automatic** — agent code should not have to remember
   to save state at every step; the orchestrator should drive it.
4. Survive process kill (`os._exit`, SIGKILL) without corrupting state —
   atomic writes only, no partial JSON on disk.
5. Keep the on-disk format human-readable so users can inspect / hand-edit
   resume points.

## Non-Goals

- **Mid-LLM-call resumption.** If a single `provider.generate_text` call is
  interrupted, that call is lost — we cannot resume from inside an HTTP
  stream. The granularity is one LLM call.
- **Branching / time-travel.** Users cannot fork a run from an earlier
  checkpoint into a parallel timeline. There is one head per story.
- **Cross-story checkpointing.** Each story has its own state.
- **Replacing the existing top-level phase model.** Sub-step checkpoints sit
  inside the existing phase boundaries; the phase list is unchanged.
- **Distributed/multi-process safety.** Only one orchestrator runs against a
  story at a time. We do not add file locks.

## User Stories

### Story author running the TUI

- As a user, I want to Ctrl+C out of a long character generation pass and
  pick up where I left off, so I do not pay for the same LLM calls twice.
- As a user, I want the TUI status line to reflect what sub-step the resume
  will pick up at, so I can predict how much work remains.
- As a user, if the process is force-killed, I want the run to resume cleanly
  rather than crashing on a malformed state file.

### Pipeline author / contributor

- As a contributor, I want a single helper API for "checkpoint this work item
  as done" so new phases inherit granular resume for free.
- As a contributor, I want sub-step checkpoints to be type-checked, not
  free-form strings, so a typo cannot silently disable resume.

## Proposed Solution

Introduce a **work-item ledger** alongside the existing `pipeline_state.json`.
Each phase that contains a loop maintains an explicit list of completed work
item IDs. Before doing a unit of work, the loop checks the ledger and skips
items already present. After successfully persisting the artefact, the loop
appends the item ID to the ledger and writes the savepoint.

### Data model addition

Add one field to `PipelineState`:

```python
completed_work_items: dict[str, list[str]] = field(default_factory=dict)
```

The dict is keyed by phase name; the value is the list of work item IDs the
phase has already completed. Examples of work item IDs:

- `characters/yara-osei/sheet`
- `characters/yara-osei/chunk:backstory`
- `characters/yara-osei/abridged`
- `characters/yara-osei/summary`
- `settings/the-command-spine/chunk:atmosphere_mood`
- `chapter-3/scene:2`
- `chapter-3/wiki-update`
- `chapter-3/sheet-evolution`
- `chapter-3/recap`
- `final-edit/chapter:5`

Work item IDs are deterministic strings derived from the loop's natural keys
(slug, chunk name, scene index). They are stable across runs.

### Helper API

A single `_mark_work_item_done(state, phase, item_id)` method:

1. Adds `item_id` to `state.completed_work_items[phase]`.
2. Atomically writes `pipeline_state.json` (existing `_write_savepoint`).

A single `_work_item_done(state, phase, item_id) -> bool` query helper.

### Per-phase changes

- **Characters / Settings:** loop over `(name, chunk)` pairs. For each
  iteration, check the ledger; skip if present; write artefact; mark done.
  Read existing on-disk JSON instead of regenerating when the ledger says
  the chunk is done. Move name extraction to its own work item
  (`characters/_extract_names`) so the extracted list is cached and not
  re-extracted on resume.
- **Outline / Critique:** outline draft → critique → revision become three
  ledger items.
- **Chapter loop, scene drafting:** persist each scene's prose as it is
  written to `chapters/chapter_N_scene_M.md` and add `chapter-N/scene:M`
  to the ledger. On resume, read scene files back into the in-memory list
  before continuing.
- **Per-chapter post-processing:** wiki-update, sheet-evolution, recap, and
  metadata-chapter-1 each become a ledger item under the chapter's phase.
- **Final edit:** per-chapter edit becomes a ledger item; edited content is
  written to disk before marking done.
- **Wiki bootstrap:** entity-by-entity ledger so a partial bootstrap resumes
  at the next entity.

### Atomic writes

`pipeline_state.json` is already written non-atomically. Move it to
`_atomic_write` (tempfile + `os.replace`) so a crash mid-write cannot leave
a truncated file. Each artefact write that backs a ledger entry must use
atomic write **before** the ledger entry is added.

### Ordering invariant

The "write artefact, then mark ledger" order is mandatory: if the process
dies between artefact and ledger, the work re-runs (correct). If the order
were reversed, a death between ledger and artefact would skip work whose
output never made it to disk (data loss).

### Backward compatibility

Existing `pipeline_state.json` files without `completed_work_items` load
with an empty dict — every loop falls back to its old behaviour for that
run only, then populates the ledger going forward.

## Acceptance Criteria

- [ ] `PipelineState.completed_work_items` field exists, serialises and
      deserialises round-trip, and defaults to empty dict on legacy files.
- [ ] `_write_savepoint` uses atomic write.
- [ ] Killing the process mid-character-generation and re-running picks up
      at the next un-checkpointed character/chunk; previously completed
      character JSON files are not overwritten.
- [ ] Killing the process mid-setting-generation has the same property.
- [ ] Killing the process mid-scene-drafting in a chapter resumes at the
      next un-drafted scene, with prior scene prose loaded from disk.
- [ ] Killing the process between chapter draft and wiki update resumes
      at the wiki update for that chapter, not at the chapter draft.
- [ ] Killing the process mid-final-edit resumes at the next unedited
      chapter.
- [ ] Killing the process mid-wiki-bootstrap resumes at the next entity.
- [ ] All artefact writes that back a ledger entry are atomic.
- [ ] No regression in the happy-path completion of an end-to-end run.
- [ ] Tests cover the resume behaviour for each phase by simulating an
      interrupt: write partial state, re-enter the phase, assert that
      LLM calls for already-done items are not made.

## Open Questions

- Should we expire / invalidate ledger entries when the user changes the
  prompt or model? Out of scope for this PRD; flag as future work — a
  prompt-hash-aware invalidation system is a separate feature.
- Do we want a CLI command to inspect the ledger (`story-writer status
  --story X`)? Nice-to-have; defer.
- Do we want to expose a "force re-do this work item" UX? Defer until users
  ask.

## Related

- Earlier in this session: wiki-bootstrap silent-completion fix (orchestrator
  no longer marks `wiki-bootstrap` complete on failure).
- Earlier in this session: scene continuity fix (per-scene prompts thread
  prior tail + completed-scenes summary).
- ADR 007 — python-native orchestration.
