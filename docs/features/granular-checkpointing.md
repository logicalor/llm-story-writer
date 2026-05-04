# Granular Checkpointing

> Work-item ledger checkpoints let interrupted runs resume from the last persisted sub-step instead of restarting whole loop-heavy phases.

## Overview

Granular checkpointing extends the existing `pipeline_state.json` savepoint model with a work-item ledger stored in `PipelineState.completed_work_items`. Instead of treating characters, settings, and chapter drafting as all-or-nothing phases, the orchestrator now records each persisted sub-step only after the backing artefact has been written to disk.

This change exists to cut wasted LLM work after an interruption. A killed run no longer needs to re-extract character names, regenerate every completed sheet chunk, or throw away already-drafted early scenes from the current chapter. Resume still starts from the latest `stories/<story>/savepoints/pipeline_state.json` snapshot, but the phase-local ledger inside that snapshot now decides which sub-steps can be skipped safely.

## Implemented Coverage

Issue #318 / PR #330 implements ADR 010 Tasks 4, 5, and 6. Issue #320 / PR #332 completes Tasks 7 through 11, extending ledger-driven resume across the remaining loop-heavy and multi-step pipeline surfaces.

### Characters Phase

`src/presentation/orchestrator.py` now threads `state: PipelineState` into `_generate_character_sheets()` and records character work under the `characters` ledger bucket.

The phase now checkpoints these persisted artefacts:

- `stories/<story>/characters/_names.json` after successful name extraction (`characters/_extract_names`)
- `stories/<story>/characters/<slug>.json` plus `stories/<story>/characters/<slug>/sheet.md` after each base sheet write (`characters/<slug>/sheet`)
- The same JSON file plus `stories/<story>/characters/<slug>/chunks/<chunk-name>.md` after each chunk write (`characters/<slug>/chunk:<chunk-name>`)
- The same JSON file plus `stories/<story>/characters/<slug>/abridged.md` and `summary.md` after `abridged` and `summary` writes (`characters/<slug>/abridged`, `characters/<slug>/summary`)

Current character chunk keys:

- `backstory`
- `personality`
- `motivation`
- `relationships`
- `skills`
- `arc`
- `current_state`

On resume, the orchestrator loads `_names.json` instead of re-running name extraction when `characters/_extract_names` is already present, then reads any already-written sheet JSON from disk and resolves its pointer refs to continue at the next missing chunk or summary step.

### Settings Phase

`src/presentation/orchestrator.py` applies the same ledger pattern to `_generate_setting_sheets()` under the `settings` ledger bucket.

The phase now checkpoints these persisted artefacts:

- `stories/<story>/settings/_names.json` after successful location extraction (`settings/_extract_locations`)
- `stories/<story>/settings/<slug>.json` plus `stories/<story>/settings/<slug>/sheet.md` after each base sheet write (`settings/<slug>/sheet`)
- The same JSON file plus `stories/<story>/settings/<slug>/chunks/<chunk-name>.md` after each chunk write (`settings/<slug>/chunk:<chunk-name>`)
- The same JSON file plus `stories/<story>/settings/<slug>/abridged.md` and `summary.md` after `abridged` and `summary` writes (`settings/<slug>/abridged`, `settings/<slug>/summary`)

Current setting chunk keys:

- `physical_description`
- `atmosphere_mood`
- `function_purpose`
- `history_background`
- `connections_relationships`
- `rules_constraints`

On resume, completed settings are read back from the existing JSON files, their pointer refs are resolved to markdown bodies, and only the missing work items run.

### Per-Scene Chapter Drafting

`src/presentation/agents/chapter_writer.py` now accepts `state: PipelineState | None = None` in both `ChapterWriterAgent.run()` and `_run_scene_pipeline()`.

When the scene pipeline is active and a pipeline state is supplied by the orchestrator, chapter drafting checkpoints these artefacts under the chapter-specific ledger bucket `chapter-<N>`:

- `stories/<story>/chapters/chapter_<N>_scenes.json` after scene decomposition (`chapter-<N>/scenes/decomposition`)
- `stories/<story>/chapters/chapter_<N>/scene_<M>.md` after each drafted scene (`chapter-<N>/scene:<M>`)

Resume behavior:

- If scene decomposition already completed, the agent loads `chapter_<N>_scenes.json` instead of regenerating the scene list.
- If one or more scene work items already completed, the agent reads those `scene_<M>.md` files back into memory and continues drafting from the first missing scene.
- Existing direct-draft callers remain compatible because `state=None` keeps the ledger optional.

### Wiki Bootstrap

`src/tools/wiki_extract.py` now exposes two narrower runtime entry points for the bootstrap phase:

- `_list_wiki_entities(story_name, *, model=None)` extracts entities from the approved outline plus character and setting sheets, deduplicates them, and returns the entity list without generating detail levels.
- `_bootstrap_single_wiki_entity(story_name, entity, *, model=None, wiki_dir=None)` generates detail levels for one entity and writes that page only if the slug does not already exist.

`src/presentation/orchestrator.py` now drives wiki bootstrap entity-by-entity under the `wiki-bootstrap` ledger bucket with `wiki-bootstrap/<slug>` work-item IDs. Each page write completes before the ledger entry is recorded.

Resume behavior:

- Completed entity slugs are skipped individually on resume.
- Existing wiki pages remain idempotent because `_bootstrap_single_wiki_entity()` returns immediately when the slug already exists.
- `bootstrap_wiki_from_story()` remains available for direct CLI or ad-hoc Python usage and still performs the full batch bootstrap in one call.

### Per-Chapter Post-Processing

The chapter loop now treats the approved chapter draft and each post-processing sub-step as separate ledger items under the chapter phase key `chapter-<N>`.

New per-chapter work items:

- `chapter-<N>/draft` — chapter generation plus persisted chapter write
- `chapter-<N>/consistency-check` — `ConsistencyCheckerAgent`
- `chapter-<N>/wiki-update` — `WikiMaintainerAgent`
- `chapter-<N>/recap` — `RecapWriterAgent`
- `chapter-<N>/metadata` — `StoryMetadataAgent` refresh after Chapter 1 only

The chapter loop gate no longer skips by comparing `len(state.approved_chapters)` to the current chapter number. It now treats `f"chapter-{N}" in state.completed_phases` as the authoritative per-chapter completion marker.

Resume behavior:

- Legacy resumes that already have an approved chapter in `state.approved_chapters` but no draft ledger entry backfill `chapter-<N>/draft` without regenerating the chapter text.
- A run interrupted after the chapter draft but before recap or sheet evolution resumes at the next missing post-processing item instead of repeating the full chapter.
- Chapter 1 metadata refresh is resumable independently from recap, wiki update, and sheet evolution.

### Final Edit

`src/presentation/agents/final_editor.py` now exposes two reusable methods:

- `build_prior_summaries(approved_chapters) -> list[str]`
- `edit_single_chapter(draft, prior_summary, chapter_number, settings) -> ChapterDraft`

`FinalEditorAgent.run()` keeps the existing public API and now delegates through those methods for backward compatibility.

`src/presentation/orchestrator.py` drives final edit chapter-by-chapter with `final-edit/chapter:<N>` work-item IDs. Each edited chapter is written atomically to `stories/<story>/chapters/chapter_<N>_edited.md` before the ledger entry is recorded.

Resume behavior:

- If `final-edit/chapter:<N>` is already present and `chapter_<N>_edited.md` exists, resume reloads the edited file instead of re-running the editor.
- If interruption happens mid-pass, already-edited chapters remain on disk and the next run starts from the first chapter without a completed final-edit ledger item.

### Outline Draft And Critique

The outline phase now checkpoints two sub-steps under the `outline` ledger bucket:

- `outline/draft` — initial outline generation written to `pipeline_state.json` before the approval gate opens
- `outline/critique` — the combined `OutlineCriticAgent` pass when critique is enabled

Resume behavior:

- If `outline/draft` is complete, the saved outline is reused and the pipeline does not regenerate it before returning to the approval gate or critique path.
- If critique completed already, the orchestrator skips the critic pass and proceeds from the saved reviewed outline.
- Legacy savepoints that already contain `"outline"` in `completed_phases` still short-circuit the section at the phase level.

### TUI Resume Status

At the start of `_continue_pipeline()`, the orchestrator now backfills a `phase_end` status event for each completed phase when `completed_work_items` is present, then emits a step event of the form `Resuming at: next step after <last_done>` for each partially completed phase.

This banner is intentionally suppressed for legacy savepoints whose `completed_work_items` dict is empty, so older runs keep their prior resume behavior.

## Work-Item ID Scheme

Work-item IDs are stable, deterministic strings derived from phase scope plus the persisted unit of work. The canonical grammar and reserved meta-items live in [Work-Item ID Convention](../planning/granular-checkpointing/work-item-ids.md).

The implemented IDs now cover:

| Phase key | Work-item ID pattern | Persisted artefact |
|---|---|---|
| `characters` | `characters/_extract_names` | `stories/<story>/characters/_names.json` |
| `characters` | `characters/<slug>/sheet` | `stories/<story>/characters/<slug>.json` + `stories/<story>/characters/<slug>/sheet.md` |
| `characters` | `characters/<slug>/chunk:<chunk-name>` | `stories/<story>/characters/<slug>.json` + `stories/<story>/characters/<slug>/chunks/<chunk-name>.md` |
| `characters` | `characters/<slug>/abridged` | `stories/<story>/characters/<slug>.json` + `stories/<story>/characters/<slug>/abridged.md` |
| `characters` | `characters/<slug>/summary` | `stories/<story>/characters/<slug>.json` + `stories/<story>/characters/<slug>/summary.md` |
| `settings` | `settings/_extract_locations` | `stories/<story>/settings/_names.json` |
| `settings` | `settings/<slug>/sheet` | `stories/<story>/settings/<slug>.json` + `stories/<story>/settings/<slug>/sheet.md` |
| `settings` | `settings/<slug>/chunk:<chunk-name>` | `stories/<story>/settings/<slug>.json` + `stories/<story>/settings/<slug>/chunks/<chunk-name>.md` |
| `settings` | `settings/<slug>/abridged` | `stories/<story>/settings/<slug>.json` + `stories/<story>/settings/<slug>/abridged.md` |
| `settings` | `settings/<slug>/summary` | `stories/<story>/settings/<slug>.json` + `stories/<story>/settings/<slug>/summary.md` |
| `outline` | `outline/draft` | `stories/<story>/savepoints/pipeline_state.json` with the generated outline before approval |
| `outline` | `outline/critique` | `stories/<story>/savepoints/pipeline_state.json` with outline critique fields populated |
| `wiki-bootstrap` | `wiki-bootstrap/<slug>` | `stories/<story>/wiki/<type>/<slug>.md` |
| `chapter-<N>` | `chapter-<N>/scenes/decomposition` | `stories/<story>/chapters/chapter_<N>_scenes.json` |
| `chapter-<N>` | `chapter-<N>/scene:<M>` | `stories/<story>/chapters/chapter_<N>/scene_<M>.md` |
| `chapter-<N>` | `chapter-<N>/draft` | `stories/<story>/chapters/chapter_<N>.md` |
| `chapter-<N>` | `chapter-<N>/consistency-check` | `stories/<story>/savepoints/pipeline_state.json` with advisory consistency output already surfaced |
| `chapter-<N>` | `chapter-<N>/wiki-update` | Updated wiki pages plus `state.wiki_batches` saved in `pipeline_state.json` |
| `chapter-<N>` | `chapter-<N>/recap` | `stories/<story>/chapters/chapter_<N>_recap.json` and `state.recaps[str(N)]` when recap data exists |
| `chapter-<N>` | `chapter-<N>/metadata` | `stories/<story>/metadata.json` after the Chapter 1 metadata refresh |
| `final-edit` | `final-edit/chapter:<N>` | `stories/<story>/chapters/chapter_<N>_edited.md` |

Slug-bearing IDs use the orchestrator's `_slugify_name()` helper, so resume must see the same normalized entity name every run.

## Resume Behavior

After a kill, crash, or manual stop, `story-writer resume --story <name>` still reloads the latest `pipeline_state.json` snapshot. The difference is what happens inside the resumed phase.

With these ADR 010 tasks implemented:

- Outline generation and optional outline critique resume from the next missing outline sub-step.
- Characters resume from the next missing extraction, chunk, abridged, or summary item.
- Settings resume from the next missing extraction, chunk, abridged, or summary item.
- Wiki bootstrap resumes from the next missing entity slug.
- Chapter drafting resumes from the next missing scene when the scene pipeline is active, and chapter post-processing resumes from the next missing draft, consistency, wiki, recap, or metadata item.
- Final edit resumes from the next missing chapter edit.
- The TUI resume banner now surfaces the last completed work item for partially completed phases when ledger data exists.

The safety rule is unchanged and critical: write the markdown body and rewrite the JSON pointer first, then mark the work item done. If the process dies before the ledger write, that sub-step reruns. If it dies after the ledger write, both artefacts are already on disk and can be loaded safely on resume.

Legacy savepoints remain compatible. Older `pipeline_state.json` files load with an empty `completed_work_items` dict, so pre-ledger runs fall back to the older phase-level behavior until the converted phase writes a new savepoint.

## Related

- [Story Orchestrator](./story-orchestrator.md)
- [Comprehensive Manual](../manual.md#14-working-with-savepoints)
- [PRD: Granular Pipeline Checkpointing](../planning/granular-checkpointing/prd.md)
- [Work-Item ID Convention](../planning/granular-checkpointing/work-item-ids.md)
