# Story Orchestrator

> Headless Python pipeline runner and agent-callable layer implemented in Issue #161 / PR #171, extended with characters and settings in Issue #182 / PR #194, consistency-result parsing in Issue #184 / PR #197, and narrative-arc plus final-edit execution in Issue #185 / PR #198.

## Overview

Issue #161 implements the first executable Python-native orchestration slice in `src/presentation/orchestrator.py`. Issue #182 extends that slice by replacing the characters and settings stubs with real sheet-generation helpers and by teaching the chapter writer to consume those generated sheets as prompt context. Issue #185 adds the missing Phase 2.5 narrative-arc pass and replaces the Phase 9 final-edit stub with a real editing agent. The current implementation still remains smaller than the long-term PRD: it runs a headless async pipeline, persists one JSON savepoint file, and coordinates Python presentation agents plus orchestrator-local helper phases through injected transport primitives.

Two entry points exist:

- `run_pipeline(story_name, gate, bus, wiki_bus)` starts a new run, writes the initial `init` savepoint, then advances through the implemented phases.
- `resume_pipeline(story_name, savepoint_name, gate, bus, wiki_bus)` reloads persisted `PipelineState` from `stories/<story>/savepoints/pipeline_state.json` and continues from the stored phase state.

This slice does not yet implement the full PRD phase map. The current code path is the authoritative behavior for documentation and testing.

## Implemented Phase Sequence

The current orchestrator runs these phases in order:

```text
Init → Outline → [Outline Gate] → Narrative Arc → Characters → Settings
→ Wiki Init → Chapter Loop → Final Edit → Assembly
```

The top-level flow lives in `run_pipeline()` and `_continue_pipeline()`.

| Phase | Controller behavior | Savepoint written |
|------|----------------------|-------------------|
| `init` | Create initial `PipelineState`, detect batch mode from gate type, ensure `stories/<story>/savepoints/` exists | `init` |
| `outline` | Run `OutlinePlannerAgent`, persist `OutlineResult`, then wait on the outline approval gate | `outline` |
| `narrative-arc` | If `state.outline_result` exists, run `StoryPlannerAgent`, stream the arc assessment onto `TokenStreamBus`, store `ArcAnalysisResult` in `state.arc_result`, and continue even if the agent raises | `arc_analysis_complete` |
| `characters` | Emit a wiki-context event, build `story_elements` from the outline, extract character names through the configured LLM, generate one sheet per extracted name, and atomically write `stories/<story>/characters/<slug>.json` | `characters` |
| `settings` | Emit a wiki-context event, build `story_elements` from the outline, extract setting names through the configured LLM, generate one sheet per extracted name, and atomically write `stories/<story>/settings/<slug>.json` | `settings` |
| `wiki-init` | Idempotently initialise `stories/<story>/wiki/` directory structure (subdirectories, `index.md`, `log.md`, `_schema.md`, `contradictions.md`). Skips if wiki already present. Must succeed before chapter-loop wiki maintenance runs. | — (no separate savepoint) |
| `chapter-loop` | For each chapter number, run chapter drafting, chapter gate handling, consistency check, emit any failed consistency findings to the token bus, append the approved draft to `state.approved_chapters`, write `stories/<story>/chapters/chapter_{N}.md`, then run wiki maintenance and per-chapter savepointing | `chapter-{N}`, then `chapter-loop` |
| `final-edit` | Unless `generation.enable_final_edit` is explicitly `false`, run `FinalEditorAgent` once per approved chapter, replace `state.approved_chapters` with the edited drafts, and write `stories/<story>/output/story_edited.md` when edited content exists | `final_edit_complete` |
| `assembly` | Read non-empty content from `state.approved_chapters`, write `stories/<story>/output/story.md`, and fail with `StoryGenerationError` if no approved chapter content exists | `assembly`, then `complete` |

Chapter count comes from `OutlineResult.chapter_outlines` when present. If the outline did not produce chapter entries, the fallback is `range(1, min(settings.wanted_chapters, 3) + 1)`.

The characters and settings phases are implemented as orchestrator helpers rather than standalone presentation agents. `_build_story_elements()` derives the prompt input directly from `OutlineResult`, so these phases do not depend on a separate outline savepoint artefact.

## Runtime Outputs

The current orchestrator writes five story-facing artifact groups during a successful run:

- `stories/<story>/savepoints/pipeline_state.json` — the persisted `PipelineState` snapshot, including `arc_result` when narrative-arc succeeds
- `stories/<story>/characters/<slug>.json` — one JSON character sheet per extracted name
- `stories/<story>/settings/<slug>.json` — one JSON setting sheet per extracted name
- `stories/<story>/chapters/chapter_{N}.md` — written immediately after chapter `N` passes the approval gate and consistency check
- `stories/<story>/output/story_edited.md` — written after Phase 9 when final-edit is enabled and at least one edited chapter contains non-empty content
- `stories/<story>/output/story.md` — written during `assembly` by joining the non-empty content of `state.approved_chapters` with blank lines

Character and setting sheets use the same on-disk shape:

```json
{
  "name": "Alice",
  "sheet": "# Alice\nHero of the story.",
  "chunks": {},
  "summary": "",
  "updated_at": "2026-04-25T12:34:56+00:00"
}
```

Filenames are derived by `_slugify_name()`: lowercase, spaces converted to `-`, non-alphanumeric characters stripped except `-`, repeated dashes collapsed, and surrounding dashes trimmed.

Assembly is guarded. If `state.approved_chapters` contains no non-empty content, `_continue_pipeline()` raises `StoryGenerationError` instead of writing an empty manuscript file. Because `final-edit` mutates `state.approved_chapters` before `assembly`, the assembled `story.md` reflects edited content when Phase 9 runs.

## Narrative Arc Behavior

After the outline approval gate resolves successfully, `_continue_pipeline()` runs `StoryPlannerAgent` before character generation.

The phase behavior is intentionally lightweight:

1. Emit one `WikiContextEvent` for the `narrative-arc` phase.
2. Load `prompts/agents/story-planner.md` lazily through `load_agent_prompt()`.
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
4. For each non-empty name that slugifies successfully, load the corresponding create prompt and request a full markdown sheet.
5. Atomically persist the resulting JSON document under the story directory.

Failure handling is intentionally permissive. If the extraction call returns malformed JSON or otherwise raises during parsing, the phase falls back to an empty name list and the pipeline continues. If generating an individual sheet fails, that sheet is skipped while the rest of the phase proceeds.

## Chapter Prompt Enrichment

`ChapterWriterAgent.run()` now reads generated sheet files from `stories/<story>/characters/*.json` and `stories/<story>/settings/*.json` before it sends the chapter prompt to the model.

For each readable JSON file:

- `name` is used as the display label
- `summary` is preferred as the abridged prompt context
- if `summary` is empty, the agent falls back to the first 300 characters of `sheet`

The agent appends those entries under `## Characters` and `## Settings` sections in the user prompt. Missing directories, unreadable files, or malformed JSON are ignored so chapter generation still proceeds.

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

## Final Edit Behavior

Phase 9 now executes real editing work through `FinalEditorAgent`.

The phase controller logic is:

1. Read `generation.enable_final_edit` from the raw config dictionary.
2. Treat the phase as enabled when the key is missing; skip only when the key is explicitly `false`.
3. For each approved chapter, call `FinalEditorAgent.run()` with `prompts/agents/final-editor.md` as the system prompt and stream the edit pass onto `TokenStreamBus`.
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

`resume_pipeline()` currently behaves as follows:

1. Load the latest persisted `PipelineState` snapshot.
2. If a `savepoint_name` was provided, verify that the name exists in `state.savepoints`.
3. If `state.status == "complete"`, close both buses and return the saved state unchanged.
4. Otherwise call `_continue_pipeline()` and skip any phase already listed in `completed_phases`.

The current implementation validates `savepoint_name`, but it does not rewind to an older savepoint snapshot. Resume always continues from the single persisted `pipeline_state.json` state.

## Agent Callable Pattern

Issue #161 also adds `src/presentation/agents/__init__.py` and five Python callables under `src/presentation/agents/`. Each callable follows the same construction pattern:

1. Accept `provider`, `config`, `bus`, and `wiki_bus` in `__init__`.
2. Load the corresponding system prompt from `prompts/agents/` through `load_agent_prompt()` on first use.
3. Build a `ModelConfig` from `config["models"]` for the relevant role.
4. Emit at least one `WikiContextEvent` before generation or analysis.
5. Stream model output through `provider.stream_text(...)` and forward every token to `TokenStreamBus.emit()`.
6. Return a typed handoff object or small structured result.

| Agent | Prompt file | Return type | Current behavior |
|------|-------------|-------------|------------------|
| `OutlinePlannerAgent` | `prompts/agents/outline-planner.md` | `OutlineResult` | Streams outline text, parses chapter outlines from JSON or `Chapter:` lines, extracts `genre` and `themes` when present |
| `StoryPlannerAgent` | `prompts/agents/story-planner.md` | `ArcAnalysisResult` | Streams one advisory arc assessment from the approved outline, truncates stored assessment text to 1000 characters, and derives `verdict_code` heuristically from the streamed output |
| `ChapterWriterAgent` | `prompts/agents/chapter-writer.md` | `ChapterDraft` | Streams a single chapter draft from outline summary plus optional revision feedback, with abridged character and setting context loaded from disk when available |
| `WikiMaintainerAgent` | none loaded at runtime | `WikiUpdateBatch` | Calls `tools.wiki_extract.update_wiki_from_chapter()` on a worker thread, persists wiki batches after each approved chapter, returns concrete `updated_pages` / `new_pages` slug lists, and emits one `WikiContextEvent` per changed page |
| `ConsistencyCheckerAgent` | `prompts/agents/consistency-checker.md` | `dict[str, Any]` | Streams analysis text, parses JSON or fenced JSON into a flattened `issues` list, and returns `passed=False` when the LLM reports critical findings |
| `FinalEditorAgent` | `prompts/agents/final-editor.md` | `FinalEditResult` | Streams one editing pass per approved chapter, falls back to the original chapter content on empty model output, and returns the replacement chapter list for assembly |
| `StoryOrchestratorAgent` | none loaded | `dict[str, Any]` | Vestigial helper that returns a static phase plan; orchestration logic lives in `orchestrator.py` |

The prompt load is lazy and instance-local in the current code. Despite the issue text describing import-time loading, the implementation caches the prompt the first time `_get_system_prompt()` runs.

## PipelineState And Handoffs

`src/application/pipeline/handoffs.py` now carries the typed cross-phase payloads used by the implemented orchestrator slice:

| Handoff | Purpose |
|------|---------|
| `ArcAnalysisResult` | Advisory narrative-arc result returned by `StoryPlannerAgent` |
| `FinalEditResult` | Final-edit summary plus replacement `edited_chapters` returned by `FinalEditorAgent` |

`PipelineState` includes these orchestration-facing fields beyond the original outline and chapter payloads:

| Field | Type | Purpose |
|------|------|---------|
| `arc_result` | `ArcAnalysisResult | None` | Persist the latest advisory narrative-arc result into `pipeline_state.json` |
| `savepoints` | `list[str]` | Ordered record of checkpoint labels written during the run |
| `status` | `str` | Run lifecycle state: defaults to `"running"`, changes to `"rejected"` or `"complete"` |

These fields round-trip through `to_dict()`, `from_dict()`, and `to_json()`. The unit tests in `tests/unit/test_orchestrator.py` assert the main behaviors built around them, including narrative-arc execution and final-edit enable/disable behavior.

## Current Scope Boundaries

The long-term migration PRD still describes additional phases and UI surfaces that are not yet wired in this implementation. Notably absent from the current code path:

- initial wiki population (wiki directory structure is initialised, but the full initial-populate pass that creates pages from outline and sheets is not yet wired)
- quality-reviewer and prose-scrubber execution
- resume-from-arbitrary-historical-savepoint behavior

Document those only when the corresponding code lands.

## Related

- [Python-Native Foundation](./python-native-foundation.md)
- [Pipeline Primitives](./pipeline-primitives.md)
- [PRD: Python-Native Orchestration and TUI](../planning/python-native-migration/prd.md)
