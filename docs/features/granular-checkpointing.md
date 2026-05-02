# Granular Checkpointing

> Work-item ledger checkpoints let interrupted runs resume from the last persisted sub-step instead of restarting whole loop-heavy phases.

## Overview

Granular checkpointing extends the existing `pipeline_state.json` savepoint model with a work-item ledger stored in `PipelineState.completed_work_items`. Instead of treating characters, settings, and chapter drafting as all-or-nothing phases, the orchestrator now records each persisted sub-step only after the backing artefact has been written to disk.

This change exists to cut wasted LLM work after an interruption. A killed run no longer needs to re-extract character names, regenerate every completed sheet chunk, or throw away already-drafted early scenes from the current chapter. Resume still starts from the latest `stories/<story>/savepoints/pipeline_state.json` snapshot, but the phase-local ledger inside that snapshot now decides which sub-steps can be skipped safely.

## Implemented Coverage

Issue #318 / PR #330 implements ADR 010 Tasks 4, 5, and 6 across three loop-heavy pipeline surfaces.

### Characters Phase

`src/presentation/orchestrator.py` now threads `state: PipelineState` into `_generate_character_sheets()` and records character work under the `characters` ledger bucket.

The phase now checkpoints these persisted artefacts:

- `stories/<story>/characters/_names.json` after successful name extraction (`characters/_extract_names`)
- `stories/<story>/characters/<slug>.json` after each base sheet write (`characters/<slug>/sheet`)
- The same JSON file after each chunk write (`characters/<slug>/chunk:<chunk-name>`)
- The same JSON file after `abridged` and `summary` writes (`characters/<slug>/abridged`, `characters/<slug>/summary`)

Current character chunk keys:

- `backstory`
- `personality`
- `motivation`
- `relationships`
- `skills`
- `arc`
- `current_state`

On resume, the orchestrator loads `_names.json` instead of re-running name extraction when `characters/_extract_names` is already present, then reads any already-written sheet JSON from disk and continues at the next missing chunk or summary step.

### Settings Phase

`src/presentation/orchestrator.py` applies the same ledger pattern to `_generate_setting_sheets()` under the `settings` ledger bucket.

The phase now checkpoints these persisted artefacts:

- `stories/<story>/settings/_names.json` after successful location extraction (`settings/_extract_locations`)
- `stories/<story>/settings/<slug>.json` after each base sheet write (`settings/<slug>/sheet`)
- The same JSON file after each chunk write (`settings/<slug>/chunk:<chunk-name>`)
- The same JSON file after `abridged` and `summary` writes (`settings/<slug>/abridged`, `settings/<slug>/summary`)

Current setting chunk keys:

- `physical_description`
- `atmosphere_mood`
- `function_purpose`
- `history_background`
- `connections_relationships`
- `rules_constraints`

On resume, completed settings are read back from the existing JSON files and only the missing work items run.

### Per-Scene Chapter Drafting

`src/presentation/agents/chapter_writer.py` now accepts `state: PipelineState | None = None` in both `ChapterWriterAgent.run()` and `_run_scene_pipeline()`.

When the scene pipeline is active and a pipeline state is supplied by the orchestrator, chapter drafting checkpoints these artefacts under the chapter-specific ledger bucket `chapter-<N>`:

- `stories/<story>/chapters/chapter_<N>_scenes.json` after scene decomposition (`chapter-<N>/scenes/decomposition`)
- `stories/<story>/chapters/chapter_<N>/scene_<M>.md` after each drafted scene (`chapter-<N>/scene:<M>`)

Resume behavior:

- If scene decomposition already completed, the agent loads `chapter_<N>_scenes.json` instead of regenerating the scene list.
- If one or more scene work items already completed, the agent reads those `scene_<M>.md` files back into memory and continues drafting from the first missing scene.
- Existing direct-draft callers remain compatible because `state=None` keeps the ledger optional.

## Work-Item ID Scheme

Work-item IDs are stable, deterministic strings derived from phase scope plus the persisted unit of work. The canonical grammar and reserved meta-items live in [Work-Item ID Convention](../planning/granular-checkpointing/work-item-ids.md).

The newly implemented IDs from this PR are:

| Phase key | Work-item ID pattern | Persisted artefact |
|---|---|---|
| `characters` | `characters/_extract_names` | `stories/<story>/characters/_names.json` |
| `characters` | `characters/<slug>/sheet` | `stories/<story>/characters/<slug>.json` |
| `characters` | `characters/<slug>/chunk:<chunk-name>` | `stories/<story>/characters/<slug>.json` |
| `characters` | `characters/<slug>/abridged` | `stories/<story>/characters/<slug>.json` |
| `characters` | `characters/<slug>/summary` | `stories/<story>/characters/<slug>.json` |
| `settings` | `settings/_extract_locations` | `stories/<story>/settings/_names.json` |
| `settings` | `settings/<slug>/sheet` | `stories/<story>/settings/<slug>.json` |
| `settings` | `settings/<slug>/chunk:<chunk-name>` | `stories/<story>/settings/<slug>.json` |
| `settings` | `settings/<slug>/abridged` | `stories/<story>/settings/<slug>.json` |
| `settings` | `settings/<slug>/summary` | `stories/<story>/settings/<slug>.json` |
| `chapter-<N>` | `chapter-<N>/scenes/decomposition` | `stories/<story>/chapters/chapter_<N>_scenes.json` |
| `chapter-<N>` | `chapter-<N>/scene:<M>` | `stories/<story>/chapters/chapter_<N>/scene_<M>.md` |

Slug-bearing IDs use the orchestrator's `_slugify_name()` helper, so resume must see the same normalized entity name every run.

## Resume Behavior

After a kill, crash, or manual stop, `story-writer resume --story <name>` still reloads the latest `pipeline_state.json` snapshot. The difference is what happens inside the resumed phase.

With these ADR 010 tasks implemented:

- Characters resume from the next missing extraction, chunk, abridged, or summary item.
- Settings resume from the next missing extraction, chunk, abridged, or summary item.
- Scene-based chapter drafting resumes from the next missing scene instead of restarting the whole chapter.

The safety rule is unchanged and critical: write the artefact first, then mark the work item done. If the process dies before the ledger write, that sub-step reruns. If it dies after the ledger write, the artefact is already on disk and can be loaded safely on resume.

Legacy savepoints remain compatible. Older `pipeline_state.json` files load with an empty `completed_work_items` dict, so pre-ledger runs fall back to the older phase-level behavior until the converted phase writes a new savepoint.

## Related

- [Story Orchestrator](./story-orchestrator.md)
- [Comprehensive Manual](../manual.md#142-savepoints-and-resume)
- [PRD: Granular Pipeline Checkpointing](../planning/granular-checkpointing/prd.md)
- [Work-Item ID Convention](../planning/granular-checkpointing/work-item-ids.md)
