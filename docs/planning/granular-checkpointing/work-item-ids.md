# Work-Item ID Convention

> Defines the stable ID grammar used by the granular pipeline checkpointing ledger in `PipelineState.completed_work_items`.

## Overview

Granular pipeline checkpointing tracks completion at the level of individual LLM-backed sub-tasks rather than only at the top-level phase boundary. Each completed unit of work is recorded under `PipelineState.completed_work_items` in [src/application/pipeline/handoffs.py](../../../src/application/pipeline/handoffs.py), keyed by phase name and persisted through the orchestrator savepoint.

The orchestrator helpers [src/presentation/orchestrator.py](../../../src/presentation/orchestrator.py) define the ledger contract:

- `_work_item_done(state, phase, item_id)` checks whether a sub-step has already completed.
- `_mark_work_item_done(state, phase, item_id)` appends the ID and writes the savepoint.

Work-item IDs must therefore be stable, deterministic strings. If the same story run is resumed after interruption, the code must derive the same ID for the same sub-task every time so already-persisted artefacts can be skipped safely.

Related:

- [PRD](./prd.md)
- [Task Breakdown](./tasks.md)

## ID Grammar

The canonical format is:

`<phase-key>/<resource-path>`

Rules:

- `/` is the segment separator.
- `<phase-key>` is the top-level ledger bucket stored in `completed_work_items`.
- `<resource-path>` may contain one or more additional segments when the work item is scoped to an entity, chapter, or nested unit.
- Fixed operation names such as `draft`, `critique`, `revision`, `sheet`, `summary`, `wiki-update`, and `metadata` remain lowercase kebab-case.
- Qualifiers that name a repeated unit use a `name:value` form inside the final segment.

Supported qualifier forms:

| Form | Meaning | Example |
|---|---|---|
| `chunk:<name>` | Named chunk within a larger sheet or prompt family | `characters/yara-osei/chunk:backstory` |
| `scene:<N>` | 1-based scene index within a chapter | `chapter-3/scene:2` |
| `chapter:<N>` | 1-based chapter index within a phase that loops over chapters | `final-edit/chapter:5` |

Reserved meta-item names:

| Item | Meaning |
|---|---|
| `_extract_names` | Cached entity-name extraction step for character generation |
| `_extract_locations` | Cached location-name extraction step for setting generation |

Underscore-prefixed items are reserved for extraction or other phase-internal metadata operations rather than user-facing artefacts.

## Phase-by-Phase IDs

The following IDs are the standard ledger entries for the phases scheduled for granular conversion in Tasks 4-10, plus the explicitly non-converted phases from the current orchestrator sequence.

### Converted Phases

| Phase key | Work-item ID | Description |
|---|---|---|
| `outline` | `outline/draft` | Initial outline generation call |
| `outline` | `outline/critique` | Outline critique pass |
| `outline` | `outline/revision` | Outline revision pass after critique |
| `characters` | `characters/_extract_names` | Extract and cache the character name list |
| `characters` | `characters/<slug>/sheet` | Generate the full character sheet |
| `characters` | `characters/<slug>/chunk:<chunk-name>` | Generate one named character chunk such as `backstory`, `personality`, or `current_state` |
| `characters` | `characters/<slug>/abridged` | Generate the abridged character sheet |
| `characters` | `characters/<slug>/summary` | Generate the character summary |
| `settings` | `settings/_extract_locations` | Extract and cache the location name list |
| `settings` | `settings/<slug>/sheet` | Generate the full setting sheet |
| `settings` | `settings/<slug>/chunk:<chunk-name>` | Generate one named setting chunk such as `physical_description` or `rules_constraints` |
| `settings` | `settings/<slug>/abridged` | Generate the abridged setting sheet |
| `settings` | `settings/<slug>/summary` | Generate the setting summary |
| `wiki-bootstrap` | `wiki-bootstrap/<entity-slug>` | Bootstrap one wiki entity page |
| `chapter-<N>` | `chapter-<N>/scenes/decomposition` | Parse and persist the scene list for chapter `<N>` before drafting scenes |
| `chapter-<N>` | `chapter-<N>/scene:<M>` | Draft scene `<M>` for chapter `<N>` |
| `chapter-<N>` | `chapter-<N>/draft` | Persist the assembled approved chapter draft |
| `chapter-<N>` | `chapter-<N>/consistency-check` | Run the post-draft consistency check for chapter `<N>` |
| `chapter-<N>` | `chapter-<N>/wiki-update` | Apply wiki updates after chapter `<N>` |
| `chapter-<N>` | `chapter-<N>/sheet-evolution` | Evolve character and setting sheets after chapter `<N>` |
| `chapter-<N>` | `chapter-<N>/recap` | Generate the recap artefact for chapter `<N>` |
| `chapter-<N>` | `chapter-<N>/metadata` | Generate per-chapter metadata extraction, currently only for chapter 1 |
| `final-edit` | `final-edit/chapter:<N>` | Final editing pass for chapter `<N>` |

### Non-Converted Phases

These orchestrator phases remain single-shot or phase-level checkpointed in ADR 010. They do not receive additional work-item IDs under the current task set.

| Phase key | Work-item IDs | Reason |
|---|---|---|
| `init` | None | Initial state setup only |
| `story-foundation` | None | Phase-level checkpoint is sufficient for the current implementation |
| `metadata-outline` | None | Single metadata generation step |
| `narrative-arc` | None | Single advisory analysis step |
| `metadata-final` | None | Single final metadata refresh step |
| `assembly` | None | Deterministic file assembly, not a repeated LLM loop |

## Naming Conventions

Entity-bearing IDs must use the same slug derivation as the orchestrator helper `_slugify_name()` in [src/presentation/orchestrator.py](../../../src/presentation/orchestrator.py):

1. Convert the source name to lowercase.
2. Replace spaces with `-`.
3. Strip characters outside `[a-z0-9-]`.
4. Collapse repeated `-` runs into a single `-`.
5. Trim leading and trailing `-`.

Examples:

| Source name | Slug | Example work-item ID |
|---|---|---|
| `Yara Osei` | `yara-osei` | `characters/yara-osei/sheet` |
| `The Command Spine` | `the-command-spine` | `settings/the-command-spine/chunk:atmosphere_mood` |
| `Captain Rho, Sr.` | `captain-rho-sr` | `wiki-bootstrap/captain-rho-sr` |

Chunk names and fixed operation names should not be re-slugified at runtime. They should be declared once in code as stable literals and reused consistently.

## Ordering Invariant

Any artefact that justifies a ledger entry must be written to disk before `_mark_work_item_done(...)` is called.

Required order:

1. Produce the artefact content.
2. Persist the artefact atomically.
3. Call `_mark_work_item_done(...)`.

This ordering is mandatory because the ledger is authoritative for skip decisions on resume. If code records the work item first and the process dies before the artefact reaches disk, the resumed run will treat the item as complete and skip it forever even though no output exists.

## Backward Compatibility

Legacy savepoints do not contain `completed_work_items`. `PipelineState.from_dict()` in [src/application/pipeline/handoffs.py](../../../src/application/pipeline/handoffs.py) loads those files with an empty dict by default.

That means:

- existing savepoints continue to load successfully;
- resumed runs from pre-ledger savepoints fall back to the old loop behavior for that run; and
- once a converted phase executes and writes a new savepoint, subsequent resumes use the granular ledger entries.

## Notes For Implementers

- Use one phase key per logical checkpoint bucket. For chapter loop work, the phase key is the concrete chapter-specific key `chapter-<N>`, not the umbrella phase name `chapter-loop`.
- Prefer fixed literals for operation names over ad hoc formatting so tests can assert exact IDs.
- If a new repeated sub-task is added later, extend the `resource-path` with another stable segment rather than inventing a second separator scheme.