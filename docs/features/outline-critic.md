# Outline Critic

> Pre-approval outline review pass that runs six critic prompts plus three arc analytics and feeds structured findings into the later narrative-arc analysis.

## Overview

Issue #300 and PR #312 add `OutlineCriticAgent` in `src/presentation/agents/outline_critic.py` and wire it into `src/presentation/orchestrator.py` between outline generation and the outline approval gate. The phase is enabled only when `generation.enable_outline_critique` is `true`.

The agent reads the current `PipelineState.outline_result`, builds one combined outline text payload from the summary plus any `chapter_outlines` and `chapter_details`, then runs two prompt groups:

1. Six `prompts/outline_review/*.md` critics.
2. Three `prompts/outline_arc/*.md` analytics: `arc_distribution`, `promise_payoff`, and `arc_synthesis`.

The result is split across disk and pipeline state. The concatenated reviewer summaries are written to `stories/<story>/outline/critic_summary.md`. The synthesized arc-analysis outputs are stored on `PipelineState.critic_summary`, `PipelineState.arc_distribution`, and `PipelineState.promise_payoff` for downstream consumption.

## Pipeline Placement

The orchestrator now runs this sequence around the outline gate:

```text
Story Foundation -> Outline Planner -> Outline Critic -> Outline Approval Gate -> Metadata Outline -> Story Planner
```

This placement matters for two reasons:

- The critic always sees the freshly generated outline before human approval.
- `StoryPlannerAgent` now receives real critique and arc-analysis inputs instead of empty strings.

If outline critique is disabled, the orchestrator skips the phase entirely and proceeds straight from outline generation to the approval gate.

## Inputs And Outputs

### Inputs

`OutlineCriticAgent.run()` consumes:

| Field | Source | Notes |
|------|--------|-------|
| `state.outline_result` | `PipelineState` | Required. The agent raises if no outline exists. |
| `settings.enable_outline_critique` | `GenerationSettings` | Gate lives in the orchestrator; the agent is not constructed when this is `false`. |
| `settings.enable_concurrent_critics` | `GenerationSettings` | Switches the six outline-review critics between sequential execution and `asyncio.gather(...)`. |
| `settings.seed` | `GenerationSettings` | Forwarded into provider calls. |

The agent uses the `initial_outline_writer` model role for all critic and arc-analysis prompts.

### Outputs

| Output | Location | Meaning |
|-------|----------|---------|
| Critic summaries file | `stories/<story>/outline/critic_summary.md` | Concatenated `summary` fields parsed from the six outline-review critics |
| Synthesized critic summary | `PipelineState.critic_summary` | Output of `prompts/outline_arc/arc_synthesis.md` |
| Arc distribution | `PipelineState.arc_distribution` | Output of `prompts/outline_arc/arc_distribution.md` |
| Promise/payoff analysis | `PipelineState.promise_payoff` | Output of `prompts/outline_arc/promise_payoff.md` |
| Phase status | `PipelineState.current_phase` and `completed_phases` | Marks `outline-critique` as complete before the outline gate opens |

## Concurrency And Runtime Behavior

The six outline-review critics are defined in `OUTLINE_CRITIC_TYPES`:

- `audiobook-producer`
- `book-club-moderator`
- `commercial-fiction-editor`
- `literary-fiction-reviewer`
- `publishing-acquisitions-editor`
- `subject-expert`

When `enable_concurrent_critics` is `false`, the agent runs them one at a time and streams each full result to `TokenStreamBus`. When it is `true`, the agent uses `asyncio.gather(...)` for the six critic calls, then filters out failures before building the file output.

Arc analytics still run sequentially after the six critics finish.

## Current Constraints

The current implementation is intentionally smaller than the original planning task.

- `outline_critique_iterations` is validated and persisted as configuration, but `OutlineCriticAgent` currently performs one critic pass per generated outline.
- `outline_min_revisions` and `outline_max_revisions` remain part of the broader outline revision configuration, but this phase does not trigger automatic outline rewrites on critic severity.
- When the outline approval gate requests `revise <feedback>`, the orchestrator now forwards `PipelineState.critic_summary`, `PipelineState.arc_distribution`, and `PipelineState.promise_payoff` back into the outline planner as critique context alongside the user's feedback.
- If a single critic prompt fails, the agent emits a skip message and continues with the remaining critics.
- If the provider is a `unittest.mock` object, the agent skips the phase entirely so unit tests can exercise orchestrator flow without live model output.

## Gate Revision Context

Issue #348 and PR #349 extend the approval-gate revision path so critique findings are not dropped on regenerate.

When the operator enters `revise <feedback>` at the outline gate, `src/presentation/orchestrator.py` rebuilds a `critic_context` string from three `PipelineState` fields before calling `OutlinePlannerAgent.run()`:

- `state.critic_summary` under `### Arc & Synthesis Summary`
- `state.arc_distribution` under `### Arc Distribution`
- `state.promise_payoff` under `### Promise / Payoff Analysis`

`src/presentation/agents/outline_planner.py` then appends that formatted block under `## Critique Analysis` beside the user's `## Revision Feedback`. The same combined revision context is also forwarded into chunked outline passes, so both `outline/create_chunk` and `outline/analyze_enrichment` receive the gate feedback plus the latest critique analysis.

## Story Planner Integration

`src/presentation/agents/story_planner.py` now loads `prompts/outline/arc_assessment_direct.md` with four inputs:

- `outline`
- `critic_summary`
- `arc_distribution`
- `promise_payoff`

That keeps the later narrative-arc assessment advisory, but makes it critique-aware when the pre-gate analysis ran successfully.

## Key Files

- `src/presentation/agents/outline_critic.py` — critic orchestration, parser integration, concurrency switch, and file write
- `src/presentation/orchestrator.py` — phase insertion between outline generation and the outline approval gate
- `src/presentation/agents/story_planner.py` — downstream prompt wiring for the new state fields
- `src/application/pipeline/handoffs.py` — `PipelineState` fields for `critic_summary`, `arc_distribution`, and `promise_payoff`
- `src/domain/value_objects/generation_settings.py` — `enable_concurrent_critics` setting and critique-related config surface

## Testing

`tests/unit/test_outline_critic_agent.py` covers both sequential and concurrent critic execution. Downstream integration is exercised through the story-planner and orchestrator tests that assert the narrative-arc phase receives populated critic fields.

## Related

- [Story Planner](./story-planner.md)
- [Story Orchestrator](./story-orchestrator.md)
- [Tools Reference](../tools.md)
- Issue #300 — OutlineCriticAgent implementation
- PR #312 — OutlineCriticAgent implementation