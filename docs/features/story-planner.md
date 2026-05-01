# Story Planner

> Phase 2.5 agent that performs advisory narrative-arc analysis after outline approval and before character generation.

## Overview

`story-planner` is implemented in `src/presentation/agents/story_planner.py` and wired into `src/presentation/orchestrator.py` by Issue #185 / PR #198. The orchestrator runs it only after the outline approval gate resolves successfully, so the agent always analyzes the approved `OutlineResult` rather than a draft under revision.

The phase is advisory only. It does not mutate the outline, it does not reopen the approval gate, and it does not block the rest of the pipeline. If the agent raises, the orchestrator emits a skip message, writes `arc_analysis_complete`, and continues into the characters phase.

## Workflow

`story-planner` currently executes one streaming LLM call:

1. Emit a `WikiContextEvent` for phase `narrative-arc`.
2. Load the direct-generation prompt `prompts/outline/arc_assessment_direct.md` via `PromptLoader.load_prompt()`.
3. Build one user prompt from `OutlineResult.summary` plus JSON-formatted `chapter_outlines` when chapter entries exist.
4. Stream the response through `provider.stream_text(...)` using the `initial_outline_writer` model role.
5. Accumulate the streamed text and return an `ArcAnalysisResult`.

The orchestrator then stores the returned object in `PipelineState.arc_result` and emits a compact summary line on the token bus.

## Inputs And Outputs

### Inputs

The orchestrator dispatches `story-planner` with:

| Field | Description |
|-------|-------------|
| `story_name` | Story identifier used in the prompt and event stream |
| `outline_result` | Approved outline summary plus optional `chapter_outlines` payload |
| `settings.seed` | Seed forwarded into `provider.stream_text(...)` |

### Output Schema

`story-planner` returns this structure:

```json
{
  "story_name": "my-story",
  "arc_assessment": "<first 1000 characters of streamed analysis>",
  "verdict_code": "minor_concerns",
  "overall_score": 0.0
}
```

### Verdict Codes

The current implementation infers `verdict_code` heuristically from the streamed text:

| Verdict | Meaning |
|--------|---------|
| `strong` | Response text does not contain `significant`, `minor`, or `concern` |
| `minor_concerns` | Response text contains `minor` or `concern` |
| `significant_issues` | Response text contains `significant` |

## Savepoint And State

Phase 2.5 persists through the normal orchestrator savepoint path rather than an internal prompt-chain savepoint set.

| Location | Purpose |
|----------|---------|
| `PipelineState.arc_result` | Persist the latest successful `ArcAnalysisResult` into `stories/<story>/savepoints/pipeline_state.json` |
| `arc_analysis_complete` savepoint | Mark Phase 2.5 complete whether analysis succeeded or was skipped after an exception |

The phase analyzes the existing outline only. It does not rewrite `OutlineResult`, create intermediate arc savepoints, or store a separate story-state field.

## Developer Notes

### Key Files

- `prompts/outline/arc_assessment_direct.md` — direct-generation prompt loaded by the Python-native agent
- `prompts/agents/story-planner.md` — OpenCode/Copilot workflow specification (not used by the Python-native runtime)
- `src/presentation/agents/story_planner.py` — prompt loading, streaming call, verdict parsing, and `ArcAnalysisResult` construction
- `src/presentation/orchestrator.py` — Phase 2.5 wiring, exception handling, token-bus summary, and savepoint persistence
- `src/application/pipeline/handoffs.py` — `ArcAnalysisResult` and `PipelineState.arc_result`

### Constraints

- Advisory only: the orchestrator catches agent failures and continues.
- One-pass only: no nested critic fan-out or prompt chain is wired in the current implementation.
- Compact persistence: `arc_assessment` is truncated to 1000 characters before storage.
- Deterministic verdict parsing: `verdict_code` comes from keyword matching, not structured JSON parsing.

## Testing

`tests/unit/test_orchestrator.py` covers both successful execution and the advisory error path with `test_narrative_arc_phase_runs_after_outline()` and `test_narrative_arc_phase_advisory_continues_on_error()`.

## Related

- [Story Orchestrator](./story-orchestrator.md)
- [Comprehensive Manual](../manual.md)
- Issue #185 — Implement final-edit phase and add narrative-arc phase
- PR #198 — Narrative-arc and final-edit implementation