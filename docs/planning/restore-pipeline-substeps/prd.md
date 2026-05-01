# PRD: Restore Skipped Pipeline Sub-Steps in the Python-Native Orchestrator

> Re-wire the dozens of generation prompts that exist on disk under `prompts/` but are never invoked by the post-ADR-007 Python-native orchestrator. Restores outline foundation work, recap continuity, full critique loops, character/setting depth, wiki bootstrap, and final-edit diagnostics — without re-introducing the legacy `outline_chapter` strategy.

**Date:** 2026-05-02
**Author:** Planner agent
**Status:** Draft

---

## Problem Statement

The Python-native orchestrator introduced in [ADR 007](../adr/007-python-native-orchestration.md) replaced the legacy `outline_chapter` strategy with a small set of agents under [src/presentation/agents/](../../../src/presentation/agents/). During that migration the agents were simplified to one-shot direct-generation calls. The richer multi-stage pipelines that the prompt corpus under `prompts/` was designed to drive were dropped, and the corresponding [`GenerationSettings`](../../../src/domain/value_objects/generation_settings.py) flags became dead.

A recent code-and-prompt audit (see "Workflow Gap Report" — recorded in `.github/notes/plans/restore-pipeline-substeps.md`) catalogued every prompt that is no longer invoked or whose required template variables are stubbed empty. The list spans every phase of the pipeline:

- **Outline foundation:** `extract_base_context`, `extract_story_start_date`, `outline/create_elements`, `outline/create_skeleton`, `outline/expand_chapter_detail`, `outline/analyze_continuity`, `outline/analyze_enrichment`, `outline/create_chunk`, `outline/strip_elements`, `outline/create_title`, `outline/create_summary`, `outline/create_tags`, plus 9 `multistep/outline/*` chunks.
- **Outline critique / arc:** `outline_arc/arc_distribution`, `outline_arc/promise_payoff`, `outline_arc/arc_synthesis` (called with empty inputs), all six `outline_review/*.md` critics.
- **Character & setting:** `create_summary`, `create_abridged`, all 7 character chunks, all 6 setting chunks, `extract_from_chapter`, `analyze_changes`, `update`.
- **Recap:** the entire `prompts/recap/` family plus `extract_chapter_events.md` and `extract_story_start_date.md`.
- **Chapter generation:** `chapters/create_outline_summary`, `chapters/create_title`, `chapters/generate_handoff`, `chapters/extract_list*`, `multistep/chapter/*`, `multistep/scene/*` (position-aware first/middle/final), `story_state/*`.
- **Chapter review:** `consistency_check_direct` is called with `outline=""`; the four secondary critics (pacing, character-consistency, voice-consistency, commercial-fiction-editor) are unused inside the loop.
- **Final edit:** `final_edit/prose_scrub` and `final_edit/voice_consistency_pass` are unused; `edit_chapter_direct` runs blind.
- **Wiki:** `wiki/extract_from_outline` and `wiki/extract_from_sheet` bootstrap flows are unused, leaving the wiki empty for the first 1–2 chapters.

The user-visible symptoms are: thin outlines, missing story metadata (title/summary/tags), chapters that share `{base_context}=""` and `{story_elements}=""`, recap continuity that degrades to "previous chapter outline blurb" past chapter 1, no critic-driven revisions, and a wiki that lags behind the prose.

## Goals

1. Every prompt under `prompts/` (excluding the deprecated `prompts/agents/` tree) is either **invoked** by the orchestrator with non-empty required variables, or **explicitly retired** by deleting the file and recording the decision in `.github/notes/deferred.md`.
2. Every flag on [`GenerationSettings`](../../../src/domain/value_objects/generation_settings.py) is either honoured by the new pipeline or removed.
3. No regression in the existing 548-test unit suite. New behaviour ships with new tests.
4. The pipeline remains fully Python-native — no re-introduction of `application/strategies/outline_chapter/`.
5. The orchestrator continues to expose the same approval-gate semantics (outline gate + per-chapter gate) and savepoint resumability.

## Non-Goals

- **No new prompt authoring.** Every restored sub-step must use a prompt that already exists on disk. Prompts that don't exist for a desired step are out of scope until a separate PRD justifies authoring them.
- **No revival of `outline_chapter` strategy code.** Reference the legacy implementation only as documentation; do not import from it.
- **No quality-score-driven auto-revision.** `outline_quality` and `chapter_quality` thresholds remain advisory. Automated revision driven by critic scores is a follow-up.
- **No new approval gates.** Sub-steps run inside existing phases; only the outline-approval and chapter-approval gates remain.
- **No UI/TUI changes** beyond emitting new progress messages on the existing token bus.
- **No model-routing changes.** Continue using the `models` map in `config.yml`; new sub-steps reuse existing model roles (`initial_outline_writer`, `chapter_outline_writer`, `scene_writer`, `checker_model`, etc.).

## User Stories

### Story author (end user)

- As a story author, I want the generated outline to include a **title, back-cover summary, and genre/theme tags** so the story is publishable without manual metadata work.
- As a story author, I want each chapter to be written against a **detailed per-chapter outline** (Opening / Beats / Character Focus / Setting & Atmosphere / Tension & Stakes / Close) so chapters land their intended consequence.
- As a story author, I want **continuity across chapters** — the recap pipeline should ensure chapter N references events from chapters 1..N-1 accurately, not just paraphrase the outline blurb.
- As a story author, I want **critic feedback to actually influence the outline and chapters**, so enabling `enable_outline_critique=true` produces a meaningful refinement.

### Pipeline operator (developer / CLI user)

- As an operator, I want to enable/disable each restored sub-step via existing `GenerationSettings` flags, so a fast-prototype config can skip enrichment while a high-quality config runs the full pipeline.
- As an operator, I want each new sub-step to write its own savepoint, so resume after a crash skips completed work.
- As an operator, I want the TUI to emit progress messages for each new sub-step so I can see what the pipeline is doing.

## Proposed Solution

### High-level approach

Group the restored sub-steps into **eight phases**, each implemented as a focused agent or orchestrator helper. Each phase reads its inputs from typed handoff objects in [src/application/pipeline/handoffs.py](../../../src/application/pipeline/handoffs.py) and writes its output back to those objects. New fields are added to handoff dataclasses — they are JSON-serialisable so existing savepoint code keeps working.

Phases run in dependency order. The new flow:

1. **Story foundation** (new) — produces `base_context`, `story_start_date`, `story_elements`. Runs before any LLM call that currently passes `""` for these slots.
2. **Outline** (extended) — `create_skeleton` → optional chunked `create_chunk` + `analyze_continuity` + `analyze_enrichment` → per-chapter `expand_chapter_detail` → `strip_elements`. Replaces the current single-shot `create_direct` call.
3. **Outline critique** (new) — runs all six `outline_review/*` critics in parallel, then `outline_arc/arc_distribution`, `outline_arc/promise_payoff`, `outline_arc/arc_synthesis`. Synthesised `critic_summary` is fed to `arc_assessment_direct` and (optionally) back into a single revision pass of the outline.
4. **Story metadata** (new) — `outline/create_title`, `outline/create_summary`, `outline/create_tags`. Persisted in `OutlineResult` and `state.json`.
5. **Character & setting depth** (extended) — keep `extract_names` + `create`, then add `create_summary` + `create_abridged` + per-aspect chunks. Add per-chapter `extract_from_chapter`, `analyze_changes`, `update` so sheets evolve as the story develops.
6. **Wiki bootstrap** (new) — run `wiki/extract_from_outline` after outline approval and `wiki/extract_from_sheet` after each character/setting sheet is written, so the wiki is populated before chapter 1.
7. **Recap pipeline** (new) — after each approved chapter, run `recap/extract_events` → `recap/enrich_event_details` → `recap/assign_event_timing` → `recap/format_json` → `recap/compact_events` → `recap/sanitize`. Persisted as `state.recaps` and threaded into the next chapter's `previous_chapter_recap` slot.
8. **Chapter review & final edit** (extended) — fix the `outline=""` stub in `consistency_check_direct`. Add the four secondary chapter critics inside the chapter loop. In final edit, run `prose_scrub` and `voice_consistency_pass` first; feed findings into `edit_chapter_direct`.

Position-aware scene drafting (`multistep/scene/create_content_first/middle/final`) replaces the current single `scenes/create_content` call inside `ChapterWriterAgent`.

`story_state/*` and `multistep/chapter/enrichment/*` prompts are evaluated against actual need: any that don't earn their keep are retired (deleted + noted in `.github/notes/deferred.md`). This keeps the goal "every prompt invoked or retired" achievable.

### Backend

- **New agents** in [src/presentation/agents/](../../../src/presentation/agents/):
  - `story_foundation.py` — base context + start date + story elements.
  - `outline_critic.py` — runs the six critics + arc analytics; synthesises `critic_summary`.
  - `recap_writer.py` — six-stage recap pipeline.
  - `character_evolver.py` / `setting_evolver.py` — per-chapter sheet updates.
- **Extended agents:**
  - `OutlinePlannerAgent` — multi-stage skeleton/chunk/expand/strip flow; returns enriched `OutlineResult`.
  - `ChapterWriterAgent` — position-aware scene drafting; consumes detailed per-chapter outlines.
  - `ConsistencyCheckerAgent` — pass real `outline` text; add secondary critics.
  - `FinalEditorAgent` — diagnostic-then-edit two-stage flow.
- **Orchestrator** — invoke new agents in dependency order; honour all dead flags; persist new savepoints.
- **Wiki bootstrap** — new helpers in `tools/_wiki_api.py` callable from the orchestrator at the right phases.

### Handoff dataclass changes

Additive only — old savepoints continue to deserialise:

- `OutlineResult` gains `base_context: str = ""`, `story_start_date: str = ""`, `story_elements: str = ""`, `chapter_skeletons: list[dict] = []`, `chapter_details: list[dict] = []`, `enrichment_suggestions: str = ""`, `title: str = ""`, `tags: list[str] = []`.
- `ChapterDraft` gains `synopsis: str = ""`, `scene_definitions: list[dict] = []`, `recap: dict = {}`, `consistency_findings: list[dict] = []`, `critic_findings: list[dict] = []`.
- `PipelineState` gains `critic_summary: str = ""`, `recaps: dict[int, dict] = {}`, `evolved_sheets: dict[str, dict] = {}`.

### Database / on-disk layout

No schema changes to ChromaDB. New on-disk artefacts under `stories/<name>/`:

- `state.json` — gains the new fields above.
- `chapters/chapter_<N>_synopsis.md`, `chapters/chapter_<N>_scenes.json` (already present), `chapters/chapter_<N>_recap.json` (new).
- `outline/skeleton.md`, `outline/details/chapter_<N>.md`, `outline/critic_summary.md`, `outline/title.md`, `outline/summary.md`, `outline/tags.json` (new).
- `characters/<slug>.json` and `settings/<slug>.json` — gain populated `summary`, `abridged`, and `chunks` fields.

### Configuration

All new sub-steps are gated by existing flags. The audit produced this mapping (see tasks doc):

| Flag                                     | New behaviour                                                          |
| ---------------------------------------- | ---------------------------------------------------------------------- |
| `expand_outline`                         | Toggles `create_skeleton` + `expand_chapter_detail`.                   |
| `use_chunked_outline_generation`         | Toggles `create_chunk` + `analyze_continuity` instead of single-pass.  |
| `enable_outline_critique`                | Toggles outline-critic phase.                                          |
| `outline_critique_iterations`            | Caps revision passes after critique.                                   |
| `enable_chapter_revisions`               | Toggles per-chapter critic-driven revision (still bounded by gate).    |
| `enable_scrubbing`                       | Toggles `prose_scrub` in final edit.                                   |
| `use_improved_recap_sanitizer`           | Toggles new sanitizer prompt vs simpler legacy form.                   |
| `use_multi_stage_recap_sanitizer`        | Toggles 6-stage recap vs single-call shortcut.                         |
| `scene_generation_pipeline`              | (already used) toggles per-scene drafting.                             |
| `outline_quality` / `chapter_quality`    | Become advisory thresholds surfaced on the bus only — documented.      |
| `outline_min/max_revisions`, `chapter_min/max_revisions` | Cap critic-driven revision counts. |

Flags that cannot be honoured after audit are deleted in a follow-up tidy-up task.

## Acceptance Criteria

- [ ] Every prompt under `prompts/` (excluding `prompts/agents/`) is either invoked by code in `src/` with all required variables non-empty, or deleted with a deferred-note entry. A grep-based test asserts the invariant.
- [ ] Every `GenerationSettings` field is either consumed by the orchestrator/agents or removed. A new unit test asserts no dead fields remain.
- [ ] `pytest tests/unit/` passes with ≥ 548 tests (current baseline) plus new tests for each restored sub-step.
- [ ] `ruff check src/ tests/` and `mypy src/` pass.
- [ ] Running `story-writer tui --story <name> --prompt prompts/sample-story.md` end-to-end produces an outline that contains: title, summary, tags, per-chapter detail blocks; characters with non-empty `summary` and `abridged`; settings with non-empty `summary`; a wiki populated before chapter 1; chapter 2 prose that references chapter 1 events accurately; a final edit pass that includes `prose_scrub` findings.
- [ ] Resume after kill at any sub-step boundary skips already-completed sub-steps and produces identical downstream output (golden test on a small fixture story).
- [ ] No code under `src/application/strategies/outline_chapter/` is imported by the new orchestrator (grep test).

## Open Questions

- **Critic concurrency.** Six outline critics + four chapter critics are independent calls. Run them sequentially (current orchestrator pattern, simpler), or in `asyncio.gather` (faster, but risk of provider rate limits)? **Proposed default:** sequential, with a config flag `enable_concurrent_critics: bool = False` to opt in.
- **Position-aware scene drafting.** `multistep/scene/create_content_first/middle/final` use 6 `understand_*` sub-prompts. Adopt the full multistep pattern, or keep one `create_content` call but pick the position-specific variant? **Proposed default:** position-specific variant only; the `understand_*` prompts are evaluated and either invoked once per chapter (cached) or retired.
- **Story metadata timing.** Title/summary/tags need at least one chapter to be informative (`create_title.md` takes `{first_chapter}`). Run after chapter 1, or at end of run? **Proposed default:** title after outline approval (no `{first_chapter}` — graceful degrade), refresh title + summary + tags after chapter 1, finalise after final edit.
- **Recap-on-revision.** When the user rejects a chapter and asks for revision, do we re-run the recap pipeline? **Proposed default:** yes — recaps are produced from the *approved* chapter content, so revision triggers a fresh recap.

## Related

- [ADR 007 — Python-native orchestration](../adr/007-python-native-orchestration.md) — the architectural baseline this plan extends.
- [ADR 004 — Progressive wiki memory system](../adr/004-progressive-wiki-memory-system.md) — wiki bootstrap rationale.
- [ADR 005 — Hybrid wiki context retrieval pipeline](../adr/005-hybrid-wiki-context-retrieval-pipeline.md) — context retrieval that benefits from earlier wiki population.
- [PRD: Python Agent Prompt Repair](../fix-python-agent-prompts/prd.md) — produced the `*_direct.md` prompts this plan now extends with the multi-stage flow.
- Workflow Gap Report — `.github/notes/plans/restore-pipeline-substeps.md` (recorded as part of this planning round).
