# Story Orchestrator

> Headless Python pipeline runner and agent-callable layer implemented for Issue #161 / PR #171.

## Overview

Issue #161 implements the first executable Python-native orchestration slice in `src/presentation/orchestrator.py`. The current implementation is intentionally smaller than the long-term PRD: it runs a headless async pipeline, persists one JSON savepoint file, and coordinates five Python agent callables through injected transport primitives.

Two entry points exist:

- `run_pipeline(story_name, gate, bus, wiki_bus)` starts a new run, writes the initial `init` savepoint, then advances through the implemented phases.
- `resume_pipeline(story_name, savepoint_name, gate, bus, wiki_bus)` reloads persisted `PipelineState` from `stories/<story>/savepoints/pipeline_state.json` and continues from the stored phase state.

This slice does not yet implement the full PRD phase map. The current code path is the authoritative behavior for documentation and testing.

## Implemented Phase Sequence

The current orchestrator runs these phases in order:

```text
Init → Outline → [Outline Gate] → Characters → Settings
→ Chapter Loop → Final Edit → Assembly
```

The top-level flow lives in `run_pipeline()` and `_continue_pipeline()`.

| Phase | Controller behavior | Savepoint written |
|------|----------------------|-------------------|
| `init` | Create initial `PipelineState`, detect batch mode from gate type, ensure `stories/<story>/savepoints/` exists | `init` |
| `outline` | Run `OutlinePlannerAgent`, persist `OutlineResult`, then wait on the outline approval gate | `outline` |
| `characters` | Emit a wiki-context event for character assembly, mark phase complete | `characters` |
| `settings` | Emit a wiki-context event for setting assembly, mark phase complete | `settings` |
| `chapter-loop` | For each chapter number, run chapter drafting, chapter gate handling, consistency check, wiki maintenance, and per-chapter savepointing | `chapter-{N}`, then `chapter-loop` |
| `final-edit` | Mark phase complete only; no editing subagent is wired yet | `final-edit` |
| `assembly` | Mark phase complete, set `status="complete"`, write terminal savepoint | `assembly`, then `complete` |

Chapter count comes from `OutlineResult.chapter_outlines` when present. If the outline did not produce chapter entries, the fallback is `range(1, min(settings.wanted_chapters, 3) + 1)`.

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
| `ChapterWriterAgent` | `prompts/agents/chapter-writer.md` | `ChapterDraft` | Streams a single chapter draft from outline summary plus optional revision feedback |
| `WikiMaintainerAgent` | `prompts/agents/wiki-maintainer.md` | `WikiUpdateBatch` | Streams evaluation text, currently returns empty `updated_pages` / `new_pages` placeholders |
| `ConsistencyCheckerAgent` | `prompts/agents/consistency-checker.md` | `dict[str, Any]` | Streams analysis text, currently returns `{"issues": [], "passed": True}` placeholder result |
| `StoryOrchestratorAgent` | none loaded | `dict[str, Any]` | Vestigial helper that returns a static phase plan; orchestration logic lives in `orchestrator.py` |

The prompt load is lazy and instance-local in the current code. Despite the issue text describing import-time loading, the implementation caches the prompt the first time `_get_system_prompt()` runs.

## PipelineState Extensions

Issue #161 extends `PipelineState` in `src/application/pipeline/handoffs.py` with two orchestration-facing fields:

| Field | Type | Purpose |
|------|------|---------|
| `savepoints` | `list[str]` | Ordered record of checkpoint labels written during the run |
| `status` | `str` | Run lifecycle state: defaults to `"running"`, changes to `"rejected"` or `"complete"` |

These fields round-trip through `to_dict()`, `from_dict()`, and `to_json()`. The four unit tests in `tests/unit/test_orchestrator.py` assert the main behaviors built around them: happy-path completion, outline rejection, chapter revision, and resume from a persisted savepoint.

## Current Scope Boundaries

The long-term migration PRD still describes additional phases and UI surfaces that are not yet wired in this implementation. Notably absent from the current code path:

- narrative-arc analysis
- character-sheet generation and setting-sheet generation subagents
- wiki initialization and initial population
- quality-reviewer, prose-scrubber, and final-editor execution
- CLI wiring and Textual TUI integration
- resume-from-arbitrary-historical-savepoint behavior

Document those only when the corresponding code lands.

## Related

- [Python-Native Foundation](./python-native-foundation.md)
- [Pipeline Primitives](./pipeline-primitives.md)
- [PRD: Python-Native Orchestration and TUI](../planning/python-native-migration/prd.md)
