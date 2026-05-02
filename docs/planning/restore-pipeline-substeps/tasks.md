# Task Breakdown: Restore Skipped Pipeline Sub-Steps

> Implements [PRD: Restore Skipped Pipeline Sub-Steps](prd.md)

**Date:** 2026-05-02
**Author:** Planner agent
**Status:** Draft

---

## Sequencing Strategy — Shortest Path

The audit identified ~12 logical groups of dropped work. They have heavy dependency overlap: most chapter-loop tasks need outline foundation; most outline tasks need `base_context` + `story_elements`; recap unlocks chapter-loop quality; wiki bootstrap is independent.

The shortest total path therefore front-loads **shared infrastructure** (Tasks 1–2), then **independent vertical slices** that each unlock real visible quality (Tasks 3–11), closing with **cleanup** (Task 12). Each task is sized to one Orchestrator dispatch (issue → branch → implement → verify → PR).

```
Task 1 (handoffs schema + foundation agent)        ─┐
                                                    ├─► Task 4 (outline metadata) ─┐
Task 2 (outline structure: skeleton+expand+strip)  ─┤                              │
                                                    ├─► Task 5 (outline critic+arc)┤
Task 3 (consistency-checker outline plumb)         ─┘                              │
                                                                                   │
Task 6 (recap pipeline)  ────────────────────────────► Task 7 (chapter-loop wire-in)
                                                                                   │
Task 8 (char/setting depth + per-chapter evolution)                                │
Task 9 (wiki bootstrap)                            ─ independent                   │
Task 10 (final-edit diagnostics)                   ─ independent                   │
Task 11 (chunked outline path)                     ─ optional, gated               │
                                                                                   │
Task 12 (dead-flag tidy + grep invariants + docs)  ◄────────────────────────────────
```

Tasks 3, 9, 10 can run in parallel with the front-loaded path. Task 11 is optional and shipped last because it's gated behind a config flag.

---

## Tasks

### Task 1: Story Foundation Agent + Handoff Schema Extensions

**Type:** backend (agent + dataclass)
**Estimated scope:** medium
**Dependencies:** none

**Description:**
Add a `StoryFoundationAgent` that runs before the outline phase and produces the three context strings every downstream prompt expects. Extend the typed handoff dataclasses to carry the new fields.

The agent invokes three existing prompts:

1. `prompts/extract_base_context.md` → `base_context` (genre, tone, setting flavour).
2. `prompts/extract_story_start_date.md` → `story_start_date` (used by recap timing).
3. `prompts/outline/create_elements.md` → `story_elements` (cast, factions, themes — referenced by every outline/chapter prompt).

Outputs persist into `OutlineResult.base_context`, `.story_start_date`, `.story_elements` and to `state.json`. The orchestrator wires the agent in as a new `_run_story_foundation()` step, called from `run()` immediately after init and before `_run_outline_phase()`.

Existing `OutlinePlannerAgent` is updated only to **read** these fields — its prompt-call signature is unchanged for now (Task 2 rewrites it).

**Acceptance Criteria:**
- [ ] `OutlineResult` gains `base_context`, `story_start_date`, `story_elements`, `chapter_skeletons`, `chapter_details`, `enrichment_suggestions`, `title`, `tags` fields with safe defaults; `from_dict` deserialises old savepoints unchanged.
- [ ] `PipelineState` gains `critic_summary`, `recaps`, `evolved_sheets` fields (used by later tasks).
- [ ] `StoryFoundationAgent.run()` returns a populated `OutlineResult` skeleton with all three foundation fields non-empty for `prompts/sample-story.md`.
- [ ] Orchestrator persists `state.json` with the new fields after the foundation phase.
- [ ] `pytest tests/unit/test_story_foundation_agent.py` and `tests/unit/test_pipeline_handoffs.py` pass.

**Key Files:**
- `src/application/pipeline/handoffs.py` — additive dataclass fields + `from_dict` updates.
- `src/presentation/agents/story_foundation.py` — new.
- `src/presentation/orchestrator.py` — invoke foundation phase, persist state.
- `tests/unit/test_story_foundation_agent.py` — new.
- `tests/unit/test_pipeline_handoffs.py` — extend.

---

### Task 2: Multi-Stage Outline Structure Pipeline

**Type:** backend (agent rewrite)
**Estimated scope:** large
**Dependencies:** Task 1

**Description:**
Rewrite `OutlinePlannerAgent` so the single-shot `outline/create_direct` call becomes a four-stage pipeline gated by `GenerationSettings.expand_outline`:

1. `outline/create_skeleton` (uses `base_context`, `story_elements`, `desired_chapters`) → high-level act/arc plan.
2. For each chapter: `outline/expand_chapter_detail` (uses `skeleton`, `previous_chapter`, `next_chapter`, `chapter_index`) → per-chapter detail block (Opening/Beats/Character Focus/Setting/Tension/Close).
3. `outline/strip_elements` → cleaned outline for downstream consumers.
4. Persist skeleton, per-chapter details, and stripped outline to `OutlineResult.chapter_skeletons` / `.chapter_details` / `.summary` plus `outline/skeleton.md` and `outline/details/chapter_<N>.md` on disk.

When `expand_outline=False`, fall back to the existing `create_direct` flow (now correctly receiving `base_context` and `story_elements`).

The single-shot fallback path remains so this task is independently testable without breaking existing fixtures.

**Acceptance Criteria:**
- [ ] With `expand_outline=True`, `OutlinePlannerAgent` produces a non-empty `chapter_skeletons` list of length `desired_chapters` and a `chapter_details` list of the same length.
- [ ] With `expand_outline=False`, behaviour matches the current single-shot path; existing tests continue to pass.
- [ ] Each chapter detail block is persisted to disk as `stories/<name>/outline/details/chapter_<N>.md`.
- [ ] Resume after kill mid-expansion skips already-written chapter details (per-chapter savepoint key `outline_detail_<N>`).
- [ ] `pytest tests/unit/test_outline_planner_agent.py -v` covers both branches.

**Key Files:**
- `src/presentation/agents/outline_planner.py` — rewrite.
- `src/application/pipeline/handoffs.py` — already extended in Task 1.
- `tests/unit/test_outline_planner_agent.py` — extend.

---

### Task 3: Consistency Checker — Plumb Real Outline

**Type:** backend (one-line plus tests)
**Estimated scope:** small
**Dependencies:** none (parallelisable with Task 1)

**Description:**
`ConsistencyCheckerAgent` currently calls `chapter_review/consistency_check_direct` with `outline=""`. Pass the chapter's outline detail (or fallback to the chapter blurb when Task 2 hasn't shipped yet) into the template. Add a regression test asserting the variable is non-empty.

**Acceptance Criteria:**
- [ ] `ConsistencyCheckerAgent.run()` reads outline from `state.outline_result.chapter_details[N-1]` when available, else `chapter_outlines[N-1]`.
- [ ] Test `test_consistency_checker_outline_plumbed` asserts the prompt's `{outline}` substitution is non-empty for a fixture chapter.
- [ ] Existing `tests/unit/test_consistency_checker_agent.py` still passes.

**Key Files:**
- `src/presentation/agents/consistency_checker.py`.
- `tests/unit/test_consistency_checker_agent.py`.

---

### Task 4: Story Metadata — Title / Summary / Tags

**Type:** backend (agent extension)
**Estimated scope:** small
**Dependencies:** Task 2

**Description:**
After outline approval, run `outline/create_title`, `outline/create_summary`, `outline/create_tags`. Persist into `OutlineResult.title`, `.summary` (overwrite the placeholder), `.tags`, and to `outline/title.md`, `outline/summary.md`, `outline/tags.json`. Refresh `title` + `summary` + `tags` after chapter 1 is approved (when `create_title.md` can use the actual first chapter prose) and again after final edit.

**Acceptance Criteria:**
- [ ] `OutlineResult.title`, `.summary`, `.tags` are non-empty after outline approval.
- [ ] After chapter 1 approval, the three fields are refreshed using chapter 1 content.
- [ ] State JSON contains the metadata; CLI surfaces it on the bus.
- [ ] `pytest tests/unit/test_story_metadata.py` covers both refresh points.

**Key Files:**
- `src/presentation/agents/story_metadata.py` — new helper module.
- `src/presentation/orchestrator.py` — call after outline gate and after chapter 1 approval.
- `tests/unit/test_story_metadata.py` — new.

---

### Task 5: Outline Critic + Arc Analytics Loop

Status: Complete in Issue #300 / PR #312.

**Type:** backend (agent + orchestrator wiring)
**Estimated scope:** large
**Dependencies:** Task 2

**Description:**
Implement `OutlineCriticAgent` that runs (when `enable_outline_critique=True`):

1. Six critics under `prompts/outline_review/*.md`. The implemented agent builds one combined outline payload from `OutlineResult.summary` plus any `chapter_outlines` and `chapter_details`, then runs the critics sequentially by default or concurrently when `enable_concurrent_critics=True`.
2. Three arc analytics under `prompts/outline_arc/*.md` — `arc_distribution`, `promise_payoff`, and `arc_synthesis`. The synthesised result populates `state.critic_summary` and feeds `StoryPlannerAgent`.
3. Persist the concatenated critic summaries to `stories/<name>/outline/critic_summary.md` and the arc-analysis outputs to `PipelineState`.

`StoryPlannerAgent` is updated to consume `state.critic_summary`, `arc_distribution`, `promise_payoff` from this agent's output instead of empty strings.

**Acceptance Criteria:**
- [x] With `enable_outline_critique=True`, all six critics + three arc prompts are invoked once per generated outline.
- [x] `state.critic_summary`, `state.arc_distribution`, and `state.promise_payoff` are persisted on `PipelineState`, and `outline/critic_summary.md` is written.
- [x] `StoryPlannerAgent` receives non-empty `critic_summary`, `arc_distribution`, `promise_payoff` inputs.
- [x] With `enable_outline_critique=False`, the orchestrator skips the critic phase entirely.
- [x] `pytest tests/unit/test_outline_critic_agent.py` and the related story-planner/orchestrator tests pass.

**Implementation Notes:**
- `outline_critique_iterations` remains part of `GenerationSettings`, but the current implementation performs one critic pass per generated outline rather than an auto-revision loop.
- `outline_min_revisions` and `outline_max_revisions` remain broader outline revision settings; the critic phase does not yet trigger automatic outline rewrites.

**Key Files:**
- `src/presentation/agents/outline_critic.py` — new.
- `src/presentation/agents/story_planner.py` — rewire inputs.
- `src/presentation/orchestrator.py` — call critic between outline-built and outline-gate.
- `src/domain/value_objects/generation_settings.py` — add `enable_concurrent_critics: bool = False`.
- `tests/unit/test_outline_critic_agent.py` — new.

---

### Task 6: Six-Stage Recap Pipeline

Status: Complete in Issue #297 / PR #309.

**Type:** backend (agent)
**Estimated scope:** large
**Dependencies:** Task 1 (needs `story_start_date`)

**Description:**
Implement `RecapWriterAgent` invoked after each *approved* chapter in the chapter loop. Delivered stages:

1. `prompts/extract_chapter_events.md` → list of events.
2. `prompts/recap/assign_event_timing.md` → events with timestamps relative to `story_start_date`.
3. `prompts/recap/enrich_event_details.md` → enriched events.
4. `prompts/recap/format_json.md` → canonical JSON.
5. `prompts/recap/compact_events.md` → compacted view for "current" recap.
6. `prompts/recap/sanitize.md` when `use_improved_recap_sanitizer=True`; otherwise `sanitised` falls back to `compact`.

Output persists to `state.recaps[str(N)]` and `stories/<name>/chapters/chapter_<N>_recap.json`.

The legacy multi-stage logic in `src/application/strategies/outline_chapter/recap_manager.py` may be referenced as documentation but **not imported** — the new agent must be a standalone presentation-layer implementation.

When `use_multi_stage_recap_sanitizer=False`, the agent runs a shortened path (`extract_chapter_events` + `recap/format_json`).

The current implementation is advisory inside `src/presentation/orchestrator.py`: recap generation runs after the wiki update, failures are logged without aborting the chapter loop, and resume reruns recap generation rather than restoring per-stage recap savepoints.

**Acceptance Criteria:**
- [x] After chapter N approval, `state.recaps[str(N)]` contains a populated dict with `events`, `compact`, `sanitised` keys.
- [x] `stories/<name>/chapters/chapter_<N>_recap.json` is written.
- [x] Recap generation failures are advisory and do not block chapter persistence or later chapters.
- [x] Both flag combinations (`use_improved_recap_sanitizer`, `use_multi_stage_recap_sanitizer`) are exercised by tests.
- [x] `pytest tests/unit/test_recap_writer_agent.py` passes.

**Key Files:**
- `src/presentation/agents/recap_writer.py` — new.
- `src/presentation/orchestrator.py` — call after chapter approval, before next chapter.
- `tests/unit/test_recap_writer_agent.py` — new.

---

### Task 7: Chapter Loop — Wire Real Recap + Position-Aware Scenes

**Type:** backend (agent edit)
**Estimated scope:** medium
**Dependencies:** Tasks 2, 6

**Description:**
Update `ChapterWriterAgent` so:

- `previous_chapter_recap` template variable receives `state.recaps[N-1].compact` (or sanitised form), not the outline blurb.
- The per-chapter outline passed to synopsis/scene prompts is the detailed block from `OutlineResult.chapter_details[N-1]`, not the skeleton blurb.
- Scene drafting branches by chapter position:
  - First chapter → `prompts/multistep/scene/create_content_first.md`.
  - Final chapter → `prompts/multistep/scene/create_content_final.md`.
  - Otherwise → `prompts/multistep/scene/create_content_middle.md` (replaces `scenes/create_content`).

When `scene_generation_pipeline=False`, fall back to the existing `chapters/write_chapter_direct` path (now also receiving real recap and detailed outline).

Evaluate the `multistep/scene/understand_*` family during implementation. Any prompt that doesn't earn its keep is deleted in Task 12.

**Acceptance Criteria:**
- [ ] Chapter 2's prompt invocation receives a non-empty `previous_chapter_recap` derived from `state.recaps[1]`.
- [ ] Chapter 1 invokes the `_first` scene prompt; final chapter invokes `_final`; middle chapters invoke `_middle`. Asserted by spying on `PromptLoader.load_prompt`.
- [ ] When `scene_generation_pipeline=False`, behaviour matches existing single-shot path; existing tests pass.
- [ ] `pytest tests/unit/test_chapter_writer_agent.py -v` covers all three position branches.

**Key Files:**
- `src/presentation/agents/chapter_writer.py`.
- `tests/unit/test_chapter_writer_agent.py`.

---

### Task 8: Character + Setting Depth and Per-Chapter Evolution

**Type:** backend (agents)
**Estimated scope:** large
**Dependencies:** Task 1

**Description:**
After the existing `extract_names` + `create` pass:

1. For each character, run `characters/create_summary` and `characters/create_abridged`. Persist to `characters/<slug>.json` fields `summary` and `abridged`. The abridged form is what gets injected into chapter prompts (token budget hygiene).
2. Same pattern for settings via `settings/create_summary` and `settings/create_abridged`.

After each approved chapter, run a `CharacterEvolverAgent` / `SettingEvolverAgent`:

3. `characters/extract_from_chapter` → events touching this character.
4. `characters/analyze_changes` → diff against current sheet.
5. `characters/update` → updated sheet (only when changes are material).

Update `state.evolved_sheets[chapter_N][slug]` for traceability.

The 7 character "chunk" prompts and 6 setting "chunk" prompts (`prompts/characters/*` and `prompts/settings/*`) are evaluated during implementation. Those that produce useful aspect-specific content (e.g. backstory, motivation) are invoked once at sheet creation; the rest are deleted in Task 12.

**Acceptance Criteria:**
- [ ] Every character and setting JSON has non-empty `summary` and `abridged` after sheet generation.
- [ ] After chapter approval, `state.evolved_sheets[N]` records any sheets that changed.
- [ ] Chapter prompts use the abridged form (asserted by length check on `{character_context}` template variable).
- [ ] `pytest tests/unit/test_character_evolver.py` and `test_setting_evolver.py` pass.

**Key Files:**
- `src/presentation/agents/character_evolver.py` — new.
- `src/presentation/agents/setting_evolver.py` — new.
- `src/presentation/orchestrator.py` — extend `_generate_character_sheets` and `_generate_setting_sheets`; wire evolvers into chapter loop.
- `tests/unit/test_character_evolver.py`, `tests/unit/test_setting_evolver.py` — new.

---

### Task 9: Wiki Bootstrap from Outline + Sheets

**Type:** backend (orchestrator wiring)
**Estimated scope:** medium
**Dependencies:** none (parallelisable)

**Description:**
The existing `_wiki_api.py` already has `wiki/extract_from_outline` and `wiki/extract_from_sheet` helpers — they're just not called. Wire them in:

1. After outline approval (and before chapter 1), call `wiki/extract_from_outline` to seed the wiki with characters/settings/lore mentioned in the outline.
2. After each character/setting sheet is generated, call `wiki/extract_from_sheet` so the wiki has a fully-populated entry by the time chapter 1 starts.

This means the existing `WikiMaintainerAgent.update_wiki_from_chapter` flow now operates against a non-empty wiki from chapter 1 onward.

**Acceptance Criteria:**
- [ ] After outline approval, `stories/<name>/wiki/` contains pages for every entity named in the outline (asserted by counting wiki page files).
- [ ] After character sheet generation, the corresponding wiki page has a populated `summary`.
- [ ] Chapter 1's wiki context retrieval (ADR 005 pipeline) returns non-empty results.
- [ ] `pytest tests/unit/test_wiki_bootstrap.py` passes.

**Key Files:**
- `src/presentation/orchestrator.py` — invoke wiki bootstrap helpers.
- `src/tools/_wiki_api.py` — minor signature tidy-up if needed.
- `tests/unit/test_wiki_bootstrap.py` — new.

---

### Task 10: Final-Edit Diagnostics — Prose Scrub + Voice Consistency

**Type:** backend (agent extension)
**Estimated scope:** medium
**Dependencies:** none (parallelisable)

**Description:**
Extend `FinalEditorAgent` to a two-stage flow:

1. **Diagnose** — for each chapter, run `final_edit/prose_scrub.md` (gated by `enable_scrubbing`) and `final_edit/voice_consistency_pass.md`. Collect findings.
2. **Edit** — pass findings as `{prose_findings}` and `{voice_findings}` template variables into the existing `edit_chapter_direct.md` call (template needs the new placeholders added — additive, backwards-compatible).

When `enable_scrubbing=False`, skip stage 1 entirely; behaviour matches current single-shot path.

**Acceptance Criteria:**
- [ ] With `enable_scrubbing=True`, `prose_scrub` and `voice_consistency_pass` are invoked once per chapter.
- [ ] `edit_chapter_direct` receives non-empty `{prose_findings}` and `{voice_findings}` (asserted by template-variable spy).
- [ ] With `enable_scrubbing=False`, behaviour matches current single-shot.
- [ ] `pytest tests/unit/test_final_editor_agent.py -v` covers both flag values.

**Key Files:**
- `src/presentation/agents/final_editor.py`.
- `prompts/final_edit/edit_chapter_direct.md` — additive placeholders only (allowed prompt edit; no new prompt files).
- `tests/unit/test_final_editor_agent.py`.

---

### Task 11: Chunked Outline Path (Optional)

**Type:** backend (agent extension)
**Estimated scope:** medium
**Dependencies:** Task 2

**Description:**
When `use_chunked_outline_generation=True` and `desired_chapters > outline_chunk_size`, replace the per-chapter `expand_chapter_detail` loop with a chunked flow:

1. Split chapters into chunks of size `outline_chunk_size`.
2. For each chunk: `outline/create_chunk` (uses skeleton + previous chunk).
3. Between chunks: `outline/analyze_continuity` to surface mismatches.
4. After all chunks: `outline/analyze_enrichment` to suggest additions; persist to `OutlineResult.enrichment_suggestions`.

The 9 `multistep/outline/*` chunks are evaluated during implementation. Any not earning their keep are deleted in Task 12.

When `use_chunked_outline_generation=False`, behaviour matches Task 2's per-chapter expansion.

**Acceptance Criteria:**
- [ ] With chunked flag enabled and 25 chapters / chunk size 5, exactly 5 chunk calls and 4 continuity calls are issued.
- [ ] `enrichment_suggestions` is non-empty after the run.
- [ ] With flag disabled, behaviour matches Task 2 (existing tests pass).
- [ ] `pytest tests/unit/test_outline_chunked.py` passes.

**Key Files:**
- `src/presentation/agents/outline_planner.py` — extend with chunked branch.
- `tests/unit/test_outline_chunked.py` — new.

---

### Task 12: Cleanup — Dead Flags, Prompt Retirement, Invariant Tests, Docs

**Type:** backend (cleanup) + docs
**Estimated scope:** medium
**Dependencies:** Tasks 1–11

**Description:**
Final pass. Three workstreams:

1. **Dead-flag tidy-up.** Walk every field on [`GenerationSettings`](../../../src/domain/value_objects/generation_settings.py). For each, confirm it's read by orchestrator/agents (grep). Delete any that remain dead. Update `configs/fast-prototype.sh` and `configs/high-quality.sh` to use only live flags.
2. **Prompt retirement.** Run a grep across `src/` for every prompt file under `prompts/` (excluding `prompts/agents/`). For each prompt with zero call sites, decide:
   - Keep + invoke (file an issue) — only if the audit missed it.
   - Delete + record in `.github/notes/deferred.md` with rationale (most cases).
3. **Invariant tests.** Add two tests to `tests/unit/test_repo_invariants.py`:
   - `test_no_dead_generation_settings`: every dataclass field is referenced in `src/` outside the dataclass file.
   - `test_no_orphan_prompts`: every `.md` under `prompts/` (excluding `prompts/agents/` and `prompts/_unused/`) has at least one call site in `src/`.
4. **Docs.** Update [docs/manual.md](../../manual.md) and [docs/features/python-native-foundation.md](../../features/python-native-foundation.md) to describe the restored sub-steps. Mark legacy `outline_chapter/` strategy as historical reference only.

**Acceptance Criteria:**
- [ ] No dead `GenerationSettings` fields remain.
- [ ] Every retained prompt has a call site; deletions are listed in `.github/notes/deferred.md`.
- [ ] `tests/unit/test_repo_invariants.py` passes and would fail if a future change reintroduced dead code.
- [ ] `docs/manual.md` reflects the restored pipeline.
- [ ] `pytest tests/unit/`, `ruff check src/ tests/`, `mypy src/` all clean.

**Key Files:**
- `src/domain/value_objects/generation_settings.py` — prune dead fields.
- `prompts/` — delete orphan files.
- `.github/notes/deferred.md` — append deletion log.
- `tests/unit/test_repo_invariants.py` — new.
- `docs/manual.md`, `docs/features/python-native-foundation.md`.

---

## Summary

| # | Task                                            | Type            | Scope  | Depends on |
|---|-------------------------------------------------|-----------------|--------|------------|
| 1 | Story Foundation Agent + handoff schema         | backend         | medium | —          |
| 2 | Multi-stage outline structure pipeline          | backend         | large  | 1          |
| 3 | Consistency Checker outline plumb               | backend         | small  | —          |
| 4 | Story metadata (title/summary/tags)             | backend         | small  | 2          |
| 5 | Outline critic + arc analytics loop             | backend         | large  | 2          |
| 6 | Six-stage recap pipeline                        | backend         | large  | 1          |
| 7 | Chapter loop: real recap + position-aware scenes| backend         | medium | 2, 6       |
| 8 | Character/setting depth + per-chapter evolution | backend         | large  | 1          |
| 9 | Wiki bootstrap from outline + sheets            | orchestrator    | medium | —          |
| 10| Final-edit diagnostics                          | backend         | medium | —          |
| 11| Chunked outline path (optional flag)            | backend         | medium | 2          |
| 12| Cleanup: dead flags, prompt retirement, docs    | cleanup + docs  | medium | 1–11       |
