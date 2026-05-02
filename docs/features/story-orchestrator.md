# Story Orchestrator

> Headless Python pipeline runner and agent-callable layer implemented in Issue #161 / PR #171, extended with characters and settings in Issue #182 / PR #194, consistency-result parsing in Issue #184 / PR #197, narrative-arc plus final-edit execution in Issue #185 / PR #198, story-foundation handoff seeding in Issue #292 / PR #304, and deeper character/setting generation plus per-chapter sheet evolution in Issue #298 / PR #310.

## Overview

Issue #161 implements the first executable Python-native orchestration slice in `src/presentation/orchestrator.py`. Issue #182 extends that slice by replacing the characters and settings stubs with real sheet-generation helpers and by teaching the chapter writer to consume those generated sheets as prompt context. Issue #185 adds the missing Phase 2.5 narrative-arc pass and replaces the Phase 9 final-edit stub with a real editing agent. Issue #292 inserts `StoryFoundationAgent` ahead of outline generation so the orchestrator can seed `OutlineResult` with `base_context`, `story_start_date`, and `story_elements` before later phases run. Issue #298 deepens the character and setting phases by generating `summary`, `abridged`, and per-aspect `chunks` fields up front, then runs dedicated evolver agents after each approved chapter to keep sheets current as the manuscript changes. Issue #299 adds `StoryMetadataAgent`, an advisory three-checkpoint metadata pass that generates story title, summary, and tags after outline approval, after the first approved chapter, and after final edit. The current implementation still remains smaller than the long-term PRD: it runs a headless async pipeline, persists one JSON savepoint file, and coordinates Python presentation agents plus orchestrator-local helper phases through injected transport primitives.

Two entry points exist:

- `run_pipeline(story_name, gate, bus, wiki_bus)` starts a new run, writes the initial `init` savepoint, then advances through the implemented phases.
- `resume_pipeline(story_name, savepoint_name, gate, bus, wiki_bus)` reloads persisted `PipelineState` from `stories/<story>/savepoints/pipeline_state.json` and continues from the stored phase state.

This slice does not yet implement the full PRD phase map. The current code path is the authoritative behavior for documentation and testing.

## Implemented Phase Sequence

The current orchestrator runs these phases in order:

```text
Init → Story Foundation → Outline → [Outline Gate] → Metadata Outline → Narrative Arc
→ Characters → Settings → Wiki Init → Wiki Bootstrap → Chapter Loop
→ [Metadata Chapter 1 after first approved chapter] → Final Edit → Metadata Final → Assembly
```

The top-level flow lives in `run_pipeline()` and `_continue_pipeline()`.

| Phase | Controller behavior | Savepoint written |
|------|----------------------|-------------------|
| `init` | Create initial `PipelineState`, detect batch mode from gate type, ensure `stories/<story>/savepoints/` exists | `init` |
| `story-foundation` | Run `StoryFoundationAgent`, extract `base_context`, `story_start_date`, and `story_elements`, seed or update `state.outline_result`, and persist those fields before outline generation | `story_foundation_complete` |
| `outline` | Run `OutlinePlannerAgent`, passing through story-foundation context. When `expand_outline=true`, the agent writes `outline/skeleton.md`, populates per-chapter detail files under `outline/details/`, persists the enriched `OutlineResult`, then waits on the outline approval gate. Revisions reuse the same foundation fields. | `outline` |
| `metadata-outline` | Run `StoryMetadataAgent` after outline approval using outline text only. Persist generated title and tags into `state.outline_result` when generation succeeds, write `stories/<story>/metadata.json`, and continue even if generation fails. | `metadata_outline_complete` |
| `narrative-arc` | If `state.outline_result` exists, run `StoryPlannerAgent`, stream the arc assessment onto `TokenStreamBus`, store `ArcAnalysisResult` in `state.arc_result`, and continue even if the agent raises | `arc_analysis_complete` |
| `characters` | Emit a wiki-context event, build `story_elements` from the outline, extract character names through the configured LLM, generate one full sheet per extracted name, then enrich each JSON file with `abridged`, `summary`, and seven `chunks` entries before the phase completes | `characters` |
| `settings` | Emit a wiki-context event, build `story_elements` from the outline, extract setting names through the configured LLM, generate one full sheet per extracted name, then enrich each JSON file with `abridged`, `summary`, and six `chunks` entries before the phase completes | `settings` |
| `wiki-init` | Idempotently initialise `stories/<story>/wiki/` directory structure (subdirectories, `index.md`, `log.md`, `_schema.md`, `contradictions.md`). Skips if wiki already present. Must succeed before chapter-loop wiki maintenance runs. | — (no separate savepoint) |
| `wiki-bootstrap` | Seed wiki pages from the approved outline plus the generated character and setting sheets. Existing slugs are skipped so reruns stay idempotent, and failures are logged without aborting later phases. | `wiki_populated` |
| `chapter-loop` | For each chapter number, run chapter drafting, chapter gate handling, consistency check, emit any failed consistency findings to the token bus, append the approved draft to `state.approved_chapters`, write `stories/<story>/chapters/chapter_{N}.md`, run wiki maintenance, run character and setting sheet evolution, then run advisory recap generation and persist recap output when available. After the first approved chapter only, run `StoryMetadataAgent` again as `metadata-chapter-1` using Chapter 1 prose and persist the refreshed metadata payload. | `chapter-{N}`, then `chapter-loop` |
| `final-edit` | Unless `generation.enable_final_edit` is explicitly `false`, run `FinalEditorAgent` once per approved chapter, replace `state.approved_chapters` with the edited drafts, and write `stories/<story>/output/story_edited.md` when edited content exists | `final_edit_complete` |
| `metadata-final` | Run `StoryMetadataAgent` after final edit using the edited Chapter 1 prose when available. Persist generated title and tags into `state.outline_result` when generation succeeds, rewrite `stories/<story>/metadata.json`, and continue even if generation fails. | `metadata_final_complete` |
| `assembly` | Read non-empty content from `state.approved_chapters`, write `stories/<story>/output/story.md`, and fail with `StoryGenerationError` if no approved chapter content exists | `assembly`, then `complete` |

Chapter count comes from `OutlineResult.chapter_outlines` when present. If the outline did not produce chapter entries, the fallback is `range(1, min(settings.wanted_chapters, 3) + 1)`.

The characters and settings phases are implemented as orchestrator helpers rather than standalone presentation agents. `StoryFoundationAgent` is the only new pre-outline presentation agent in this slice. Its outputs are forwarded into the initial outline call and the outline revision loop, then preserved on `OutlineResult` even when `OutlinePlannerAgent` returns a fresh object.

## Runtime Outputs

The current orchestrator writes these story-facing artifact groups during a successful run:

- `stories/<story>/savepoints/pipeline_state.json` — the persisted `PipelineState` snapshot, including `arc_result`, `recaps`, and `evolved_sheets` when those phases succeed
- `stories/<story>/outline/skeleton.md` and `stories/<story>/outline/details/chapter_{N}.md` — Phase 3 outline artifacts written when `generation.expand_outline` is enabled; existing chapter detail files are reused on resume
- `stories/<story>/metadata.json` — advisory story metadata rewritten after successful `metadata-outline`, `metadata-chapter-1`, and `metadata-final` runs; stores `title`, `summary`, `tags`, and `updated_at`
- `stories/<story>/characters/<slug>.json` — one JSON character sheet per extracted name
- `stories/<story>/settings/<slug>.json` — one JSON setting sheet per extracted name
- `stories/<story>/chapters/chapter_{N}.md` — written immediately after chapter `N` passes the approval gate and consistency check
- `stories/<story>/chapters/chapter_{N}_recap.json` — written after chapter `N` recap generation returns a non-empty recap payload
- `stories/<story>/output/story_edited.md` — written after Phase 9 when final-edit is enabled and at least one edited chapter contains non-empty content
- `stories/<story>/output/story.md` — written during `assembly` by joining the non-empty content of `state.approved_chapters` with blank lines

Character and setting sheets use the same on-disk shape:

```json
{
  "name": "Alice",
  "sheet": "# Alice\nHero of the story.",
  "chunks": {},
  "abridged": "Short prompt-safe version of the sheet.",
  "summary": "",
  "updated_at": "2026-04-25T12:34:56+00:00"
}
```

Filenames are derived by `_slugify_name()`: lowercase, spaces converted to `-`, non-alphanumeric characters stripped except `-`, repeated dashes collapsed, and surrounding dashes trimmed.

Assembly is guarded. If `state.approved_chapters` contains no non-empty content, `_continue_pipeline()` raises `StoryGenerationError` instead of writing an empty manuscript file. Because `final-edit` mutates `state.approved_chapters` before `assembly`, the assembled `story.md` reflects edited content when Phase 9 runs.

## Story Metadata Behavior

`StoryMetadataAgent` wraps three existing direct-generation prompts:

- `prompts/outline/create_title.md`
- `prompts/outline/create_summary.md`
- `prompts/outline/create_tags.md`

The orchestrator calls the agent at three checkpoints:

1. `metadata-outline` after outline approval, passing outline text and an empty Chapter 1 string.
2. `metadata-chapter-1` immediately after Chapter 1 is approved, passing the approved prose.
3. `metadata-final` after final edit, passing the edited Chapter 1 prose when available.

All three checkpoints are advisory. Each individual LLM call inside `StoryMetadataAgent.run()` is wrapped in `try/except`, and each checkpoint call in the orchestrator is also wrapped in `try/except`, so metadata generation can fail without blocking the rest of the pipeline.

Persistence behavior is intentionally split:

- `state.outline_result.title` is refreshed at each successful checkpoint.
- `state.outline_result.tags` is refreshed at each successful checkpoint.
- The generated summary is written to `stories/<story>/metadata.json`, not back into `OutlineResult.summary`.

`metadata.json` uses this shape:

```json
{
  "title": "Example Title",
  "summary": "Back-cover style summary text.",
  "tags": ["science fiction", "first contact"],
  "updated_at": "2026-05-01T21:49:38+00:00"
}
```

## Narrative Arc Behavior

After the outline approval gate resolves successfully, `_continue_pipeline()` runs `StoryPlannerAgent` before character generation.

The phase behavior is intentionally lightweight:

1. Emit one `WikiContextEvent` for the `narrative-arc` phase.
2. Load the direct-generation prompt `prompts/outline/arc_assessment_direct.md` via `PromptLoader.load_prompt()`.
3. Build one prompt from `OutlineResult.summary` plus JSON-formatted `chapter_outlines`.
4. Stream the model response through `TokenStreamBus` and accumulate the full text.
5. Store `ArcAnalysisResult(story_name, arc_assessment, verdict_code, overall_score)` in `state.arc_result`.

The phase is advisory only. The orchestrator catches all exceptions from `StoryPlannerAgent.run()`, emits `[Narrative Arc] arc analysis skipped (error)` on the token bus, still writes the `arc_analysis_complete` savepoint, and continues into `characters`.

`ArcAnalysisResult` is intentionally small in the current implementation:

- `arc_assessment` is truncated to the first 1000 characters of streamed output
- `verdict_code` is inferred heuristically from the returned text (`significant` → `significant_issues`, `minor` or `concern` → `minor_concerns`, else `strong`)
- `overall_score` is currently fixed at `0.0`

## Characters And Settings Behavior

Both sheet-generation helpers follow the same pattern:

1. Build a `story_elements` string from `OutlineResult.summary` plus serialized `chapter_outlines`.
2. Load an extraction prompt from `prompts/characters/extract_names.md` or `prompts/settings/extract_names.md`.
3. Ask the configured `chapter_writer` model for a JSON array of names.
4. For each non-empty name that slugifies successfully, load the corresponding `create` prompt and request a full markdown sheet.
5. Write the initial JSON document to disk so later summarisation prompts can read a stable object shape.
6. Run `create_abridged`, `create_summary`, and the per-aspect chunk prompts for that entity.
7. Rewrite the same JSON file with populated `chunks`, `abridged`, `summary`, and refreshed `updated_at`.

Characters currently generate seven chunks: `backstory`, `personality`, `motivation`, `relationships`, `skills`, `arc`, and `current_state`. Settings currently generate six chunks: `physical_description`, `atmosphere_mood`, `function_purpose`, `history_background`, `connections_relationships`, and `rules_constraints`.

Failure handling is intentionally permissive. If the extraction call returns malformed JSON or otherwise raises during parsing, the phase falls back to an empty name list and the pipeline continues. If generating an individual sheet fails, that sheet is skipped while the rest of the phase proceeds.

## Chapter Prompt Enrichment

`ChapterWriterAgent.run()` now reads generated sheet files from `stories/<story>/characters/*.json` and `stories/<story>/settings/*.json` before it sends the chapter prompt to the model.

For each readable JSON file:

- `name` is used as the display label
- `abridged` is preferred as the prompt context
- if `abridged` is empty, the agent falls back to `summary`
- if both short forms are empty, the agent falls back to the first 300 characters of `sheet`

The agent appends those entries under `## Characters` and `## Settings` sections in the user prompt. Missing directories, unreadable files, or malformed JSON are ignored so chapter generation still proceeds.

## Sheet Evolution Behavior

After wiki maintenance completes for an approved chapter, `_continue_pipeline()` instantiates `CharacterEvolverAgent` and `SettingEvolverAgent` before recap generation.

Both evolvers follow the same chapter-local flow for every existing sheet JSON file:

1. Run `extract_from_chapter` against the approved chapter prose.
2. Run `analyze_changes` with the current JSON sheet and extracted chapter events.
3. If the analysis indicates an update is needed, run `update` and rewrite the sheet JSON on disk.
4. Preserve the existing `abridged`, `summary`, and `chunks` fields while replacing `sheet` and `updated_at`.

The orchestrator records the per-chapter outcome in `PipelineState.evolved_sheets[str(chapter_number)]` using this shape:

```json
{
  "characters": {"Alice": "updated", "Bob": "unchanged"},
  "settings": {"Europa Base": "updated"}
}
```

Entity-level failures are advisory. An exception while processing one sheet marks that entity as `unchanged`, emits a token-bus message, and lets the rest of the chapter loop continue.

## Consistency Check Behavior

After a chapter draft clears the chapter approval gate, `_continue_pipeline()` calls `ConsistencyCheckerAgent.run()` with the story name, chapter number, and draft content.

The agent now accumulates the streamed model output into one `full_text` buffer and parses that response through `_extract_consistency_result()`. The parser accepts plain JSON plus fenced code blocks such as ```json ... ```, then normalizes findings into a flat `issues` list with `type`, `description`, and `severity` fields.

The current implementation maps these LLM response sections into issues:

- `wiki_lint_findings.contradictions` → critical `contradiction` issues
- `wiki_lint_findings.timeline_issues` → warning `timeline` issues
- `wiki_lint_findings.trait_drift` → warning `trait_drift` issues
- `semantic_findings` → `semantic` issues using the returned severity
- `cross_chapter_findings` → warning `cross_chapter` issues

`passed` is derived from `has_critical_findings`. When that flag is `true`, the returned result is `{"issues": [...], "passed": false}`. If the model response cannot be parsed as JSON, the helper falls back to `{"issues": [], "passed": true}` so the pipeline degrades gracefully instead of crashing on malformed output.

The orchestrator does not currently reject or revise the chapter automatically on consistency findings. Instead, when `passed` is `false`, it emits a `[Consistency] Chapter N — issues found:` header and one line per issue onto `TokenStreamBus`, then continues with chapter persistence and wiki maintenance.

## Recap Behavior

After wiki maintenance completes for an approved chapter, `_continue_pipeline()` instantiates `RecapWriterAgent` and dispatches it with the approved chapter text, the best available previous recap string, the story-foundation `story_start_date`, and the active `GenerationSettings`.

The orchestrator treats recap generation as advisory only:

1. Read the prior recap from `PipelineState.recaps[str(N-1)]`, preferring `sanitised`, then `compact`, then `events`.
2. Call `RecapWriterAgent.run()`.
3. If the returned recap contains a non-empty `events` field, persist it to `PipelineState.recaps[str(N)]` and write `stories/<story>/chapters/chapter_{N}_recap.json`.
4. If the agent raises, emit a `[Recap] chapter N recap skipped (...)` message and continue the chapter loop.

Two recap modes are currently wired:

- multi-stage mode when `generation.use_multi_stage_recap_sanitizer` is `true`
- short extract-plus-format mode when that flag is `false`

Within multi-stage mode, `generation.use_improved_recap_sanitizer` controls whether the final sanitize prompt runs or whether `sanitised` falls back to `compact`.

## Final Edit Behavior

Phase 9 now executes real editing work through `FinalEditorAgent`.

The phase controller logic is:

1. Read `generation.enable_final_edit` from the raw config dictionary.
2. Treat the phase as enabled when the key is missing; skip only when the key is explicitly `false`.
3. For each approved chapter, call `FinalEditorAgent.run()`, which loads `prompts/final_edit/edit_chapter_direct.md` via `PromptLoader.load_prompt()` as the system prompt, and stream the edit pass onto `TokenStreamBus`.
4. Replace `state.approved_chapters` with `FinalEditResult.edited_chapters`.
5. Write `stories/<story>/output/story_edited.md` from the edited chapter contents when at least one edited chapter is non-empty.
6. Persist `final_edit_complete` before entering `assembly`.

`FinalEditorAgent` preserves the original chapter text when the model returns only whitespace. The agent currently reports `chapters_processed`, `total_issues_found`, and `total_revisions_made`, but the last two counters are placeholder values rather than parsed review metrics.

## Approval Gate Semantics

The orchestrator is transport-agnostic. It receives an `ApprovalGate` implementation and never reads from stdin or the UI directly.

Gate outcomes map to pipeline behavior like this:

| Decision shape | Meaning | Result |
|----------------|---------|--------|
| `approved=True` | Approve | Continue immediately |
| `approved=False` and `feedback is None` | Reject | Set `PipelineState.status = "rejected"`, write savepoint, return early |
| `approved=False` and `feedback` present | Revise | Re-run current phase with `## Revision Feedback` appended to the user prompt, then await another decision |

The outline gate is handled by `_await_outline_approval()`. The chapter gate is handled by `_generate_chapter_with_gate()`.

In batch mode, callers pass `NullApprovalGate`. `run_pipeline()` records `batch_mode=True` when the injected gate class name is `NullApprovalGate`, and every gate resolves immediately with `ApprovalDecision(approved=True, auto_approved=True)`.

## Savepoints And Resume

Savepoints are persisted as a single JSON snapshot of `PipelineState` at `stories/<story>/savepoints/pipeline_state.json`. The orchestrator updates three related fields together:

- `current_phase` tracks the active or most recently completed phase.
- `savepoint_id` stores the latest savepoint label.
- `savepoints` accumulates the labels written so far.

`_mark_phase_complete()` is the standard path for successful phase completion. It appends the phase to `completed_phases`, updates `savepoint_id`, appends to `savepoints`, and writes the snapshot.

`resume_pipeline()` behaves as follows:

1. Load the latest persisted `PipelineState` snapshot.
2. If a `savepoint_name` was provided, verify that the name exists in `state.savepoints`.
3. If `state.status == "complete"`, close both buses and return the saved state unchanged.
4. Otherwise call `_continue_pipeline()` and skip any phase already listed in `completed_phases`.

Named savepoints are **validation-only**. Resume always continues from the single latest `pipeline_state.json` snapshot. The `savepoint_name` argument only verifies that the story reached at least that phase; it never restores an older snapshot.

## Agent Callable Pattern

Issue #161 adds the first Python callables under `src/presentation/agents/`, and later issues extend that set. Each callable follows the same construction pattern:

1. Accept `provider`, `config`, `bus`, and `wiki_bus` in `__init__`.
2. Load the corresponding direct-generation prompt from `prompts/` via `PromptLoader.load_prompt()` on first use.
3. Build a `ModelConfig` from `config["models"]` for the relevant role.
4. Emit at least one `WikiContextEvent` before generation or analysis.
5. Stream model output through `provider.stream_text(...)` and forward every token to `TokenStreamBus.emit()`.
6. Return a typed handoff object or small structured result.

| Agent | Direct-generation prompt | Return type | Current behavior |
|------|--------------------------|-------------|------------------|
| `StoryFoundationAgent` | `prompts/extract_base_context.md`, `prompts/extract_story_start_date.md`, `prompts/outline/create_elements.md` | `OutlineResult` | Runs before outline generation, emits a `story-foundation` wiki-context event, and returns an `OutlineResult` seeded with `base_context`, `story_start_date`, and `story_elements` |
| `OutlinePlannerAgent` | `prompts/outline/create_skeleton.md`, `prompts/outline/expand_chapter_detail.md`, `prompts/outline/strip_elements.md`, fallback `prompts/outline/create_direct.md` | `OutlineResult` | Runs a multi-stage outline pipeline when `expand_outline=true`, persists outline artifacts under `stories/<story>/outline/`, reuses existing chapter detail files on resume, and falls back to one direct outline call when expansion is disabled |
| `StoryMetadataAgent` | `prompts/outline/create_title.md`, `prompts/outline/create_summary.md`, `prompts/outline/create_tags.md` | `StoryMetadataResult` | Runs at `metadata-outline`, `metadata-chapter-1`, and `metadata-final`, emits advisory token-bus updates, parses JSON tag arrays, and rewrites `stories/<story>/metadata.json` without blocking the pipeline on failure |
| `StoryPlannerAgent` | `prompts/outline/arc_assessment_direct.md` | `ArcAnalysisResult` | Streams one advisory arc assessment from the approved outline, truncates stored assessment text to 1000 characters, and derives `verdict_code` heuristically from the streamed output |
| `ChapterWriterAgent` | `prompts/chapters/write_chapter_direct.md` plus scene-pipeline prompts when enabled | `ChapterDraft` | Builds each chapter from the best available detailed outline block, forwards prior chapter recap continuity from `PipelineState.recaps`, and either drafts scenes sequentially with first/middle/final scene prompts or falls back to direct whole-chapter drafting for revisions and pipeline fallback |
| `WikiMaintainerAgent` | none loaded at runtime | `WikiUpdateBatch` | Calls `tools.wiki_extract.update_wiki_from_chapter()` on a worker thread, persists wiki batches after each approved chapter, returns concrete `updated_pages` / `new_pages` slug lists, and emits one `WikiContextEvent` per changed page |
| `CharacterEvolverAgent` | `prompts/characters/extract_from_chapter.md`, `prompts/characters/analyze_changes.md`, `prompts/characters/update.md` | `dict[str, str]` | Runs after each approved chapter, updates character sheet `sheet` bodies in place when the analysis says a change is needed, and reports per-character `updated` or `unchanged` status back to the orchestrator |
| `SettingEvolverAgent` | `prompts/settings/extract_from_chapter.md`, `prompts/settings/analyze_changes.md`, `prompts/settings/update.md` | `dict[str, str]` | Runs after each approved chapter, updates setting sheet `sheet` bodies in place when the analysis says a change is needed, and reports per-setting `updated` or `unchanged` status back to the orchestrator |
| `RecapWriterAgent` | `prompts/extract_chapter_events.md`, `prompts/recap/assign_event_timing.md`, `prompts/recap/enrich_event_details.md`, `prompts/recap/format_json.md`, `prompts/recap/compact_events.md`, optional `prompts/recap/sanitize.md` | `dict[str, str]` | Runs after wiki maintenance for each approved chapter, emits stage banners on the token bus, and returns the `events` / `compact` / `sanitised` recap payload stored in `PipelineState.recaps` |
| `ConsistencyCheckerAgent` | `prompts/chapter_review/consistency_check_direct.md` | `dict[str, Any]` | Streams analysis text, parses JSON or fenced JSON into a flattened `issues` list, and returns `passed=False` when the LLM reports critical findings |
| `FinalEditorAgent` | `prompts/final_edit/edit_chapter_direct.md` | `FinalEditResult` | Streams one editing pass per approved chapter, falls back to the original chapter content on empty model output, and returns the replacement chapter list for assembly |
| `StoryOrchestratorAgent` | none loaded | `dict[str, Any]` | Vestigial helper that returns a static phase plan; orchestration logic lives in `orchestrator.py` |

Each agent instantiates `PromptLoader` on demand inside `run()` and loads the direct-generation prompt with runtime variables at call time. `PromptLoader` caches loaded prompt bodies for the process lifetime, so repeated calls for the same prompt path return the cached body without disk I/O.

## PipelineState And Handoffs

`src/application/pipeline/handoffs.py` now carries the typed cross-phase payloads used by the implemented orchestrator slice:

| Handoff | Purpose |
|------|---------|
| `StoryMetadataResult` | Metadata payload returned by `StoryMetadataAgent`, carrying generated title, summary, and tags for on-disk persistence |
| `OutlineResult` | Outline payload plus preserved story-foundation fields; `title` and `tags` are refreshed by metadata checkpoints while `summary` remains the structural outline summary |
| `ChapterDraft` | Approved chapter payload plus synopsis, scene definitions, recap, and review findings |
| `ArcAnalysisResult` | Advisory narrative-arc result returned by `StoryPlannerAgent` |
| `FinalEditResult` | Final-edit summary plus replacement `edited_chapters` returned by `FinalEditorAgent` |

`PipelineState` includes these orchestration-facing fields beyond the original outline and chapter payloads:

| Field | Type | Purpose |
|------|------|---------|
| `arc_result` | `ArcAnalysisResult | None` | Persist the latest advisory narrative-arc result into `pipeline_state.json` |
| `critic_summary` | `str` | Reserved persisted field for later outline-critique synthesis stages; defaults to `""` for old savepoints |
| `recaps` | `dict[str, Any]` | Persisted per-chapter recap map keyed by string chapter number; defaults to `{}` for old savepoints |
| `evolved_sheets` | `dict[str, Any]` | Persisted per-chapter sheet-evolution map keyed by string chapter number, with nested `characters` and `settings` status dicts; defaults to `{}` for old savepoints |
| `savepoints` | `list[str]` | Ordered record of checkpoint labels written during the run |
| `status` | `str` | Run lifecycle state: defaults to `"running"`, changes to `"rejected"` or `"complete"` |

These fields round-trip through `to_dict()`, `from_dict()`, and `to_json()`. `from_dict()` supplies safe defaults so savepoints created before Issue #292 still load cleanly. The unit tests in `tests/unit/test_orchestrator.py` assert the main behaviors built around them, including story-foundation execution, narrative-arc execution, and final-edit enable/disable behavior.

## Current Scope Boundaries

The long-term migration PRD still describes additional phases and UI surfaces that are not yet wired in this implementation. Notably absent from the current code path:

- quality-reviewer and prose-scrubber execution
- resume-from-arbitrary-historical-savepoint behavior

Document those only when the corresponding code lands.

## Related

- [Python-Native Foundation](./python-native-foundation.md)
- [Pipeline Primitives](./pipeline-primitives.md)
- [PRD: Python-Native Orchestration and TUI](../planning/python-native-migration/prd.md)
