# Recap Writer Agent

> Post-approval chapter recap pipeline that generates persisted recap artefacts for cross-chapter continuity.

## Overview

`RecapWriterAgent` is implemented in `src/presentation/agents/recap_writer.py` and wired into the chapter loop in `src/presentation/orchestrator.py` by Issue #297 / PR #309. The orchestrator runs it only after a chapter passes the approval gate, after chapter content is written to disk, and after the wiki-maintenance step completes.

The phase is advisory. A recap failure must not discard an approved chapter or block later chapters. If recap generation raises, the orchestrator emits a skip message on the token bus and continues the chapter loop without writing recap output for that chapter.

## Workflow

The default path is a six-stage LLM pipeline:

1. Load `prompts/extract_chapter_events.md` with the chapter body plus the prior recap string.
2. Load `prompts/recap/assign_event_timing.md` with the extracted events, `story_start_date`, and prior recap.
3. Load `prompts/recap/enrich_event_details.md` with the timed events.
4. Load `prompts/recap/format_json.md` with the enriched events.
5. Load `prompts/recap/compact_events.md` with the formatted JSON recap.
6. When `settings.use_improved_recap_sanitizer` is `true`, load `prompts/recap/sanitize.md` with the compact recap, `story_start_date`, and prior recap.

`RecapWriterAgent` calls `provider.generate_text(...)` for each stage and emits both stage banners and non-empty stage outputs onto `TokenStreamBus`.

### Short Path

When `settings.use_multi_stage_recap_sanitizer` is `false`, the agent skips the timing, enrichment, compacting, and sanitize stages. It runs only:

1. `extract_chapter_events`
2. `recap/format_json`

In that path, the returned `compact` and `sanitised` values are both the formatted JSON string.

## Inputs And Outputs

### Inputs

The orchestrator dispatches the agent with:

| Field | Description |
|-------|-------------|
| `story_name` | Story identifier used in the wiki-context event stream |
| `chapter_number` | Approved chapter number being recapped |
| `chapter_content` | Final approved chapter manuscript |
| `previous_recap` | Best available prior recap text; the orchestrator prefers `sanitised`, then `compact`, then `events` from `PipelineState.recaps[str(N-1)]` |
| `story_start_date` | Foundation-phase date string forwarded into the timing and sanitize stages |
| `settings` | `GenerationSettings` flags and seed |

### Output Schema

`RecapWriterAgent.run()` returns this structure:

```json
{
  "events": "<raw stage-1 events text>",
  "compact": "<compact recap or formatted JSON in short mode>",
  "sanitised": "<sanitize output or compact fallback>"
}
```

If stage 1 fails or returns an empty string, the agent returns empty strings for all three fields and the orchestrator skips recap persistence.

## Persistence And State

When the returned recap contains a non-empty `events` field, the orchestrator writes the recap to both runtime state and disk:

| Location | Purpose |
|----------|---------|
| `PipelineState.recaps[str(N)]` | Persist the per-chapter recap inside `stories/<story>/savepoints/pipeline_state.json` |
| `stories/<story>/chapters/chapter_<N>_recap.json` | Persist the same recap object as an on-disk chapter artefact |

The recap file contains the same three top-level keys: `events`, `compact`, and `sanitised`.

The current implementation does not write per-stage recap savepoints. On resume, the orchestrator reloads the latest `PipelineState` snapshot and reruns recap generation for any chapter that has not yet completed the chapter loop in that snapshot.

## Model And Prompt Routing

`RecapWriterAgent` resolves its model role through `_build_model_config()`:

- Preferred role: `models.recap_writer`
- Fallback role: `openai-compat://default`

Prompt loading stays entirely inside the Python-native runtime. The agent uses `PromptLoader` against the repository `prompts/` directory and never loads `prompts/agents/*.md` workflow specs.

## Testing

`tests/unit/test_recap_writer_agent.py` covers the current agent contract:

- full six-call path with sanitize enabled
- short two-call path when `use_multi_stage_recap_sanitizer=False`
- five-call path when `use_improved_recap_sanitizer=False`
- empty-result fallback when stage 1 fails
- stage-banner emission on the token bus
- acceptance of empty prior recap and story-start-date inputs

Related orchestrator coverage in `tests/unit/test_orchestrator.py` verifies that recap results are stored under `PipelineState.recaps` and written to `chapter_<N>_recap.json` during the chapter loop.

## Related

- [Story Orchestrator](./story-orchestrator.md)
- [Tools Reference](../tools.md)
- [Comprehensive Manual](../manual.md)
- Issue #297 — Implement `RecapWriterAgent`
- PR #309 — Documentation and shipped recap-agent wiring