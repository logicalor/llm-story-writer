# Story Planner

> Phase 2.5 subagent that evaluates the finalized outline's dramatic arc before the human approval gate.

## Overview

`story-planner` runs after the orchestrator has saved the final outline at `outline_complete` and before the user approves the story for downstream generation. Its job is to add a structured narrative-arc review surface without reopening the nested-agent depth problems that previously caused orchestration instability.

The subagent is advisory only. It does not trigger an automatic rewrite loop and it does not block batch mode. Instead, it returns a compact arc report that the orchestrator presents during Phase 3 alongside the normal outline summary.

## Workflow

`story-planner` executes a fixed tool-only pipeline:

1. Read the finalized `outline` from story state.
2. Read `story_elements` from story state and extract a working genre label.
3. Run the six `outline_review/` critics through `critique-runner` in `outline` mode.
4. Load and apply the arc-analysis prompts in `prompts/outline_arc/`.
5. Synthesize one dramatic arc assessment.
6. Save the result to `arc_analysis_complete`.
7. Return the structured assessment payload to the orchestrator.

Because the agent calls tools only, orchestration depth stays at 1. The orchestrator remains responsible for user interaction and for any outline regeneration if the user decides the arc findings warrant a rewrite.

## Inputs And Outputs

### Inputs

The orchestrator dispatches `story-planner` with:

| Field | Description |
|-------|-------------|
| `story_name` | Story identifier used for all `story-state` and savepoint operations |
| `outline_quality` | Configured outline-quality threshold, passed through for consistent reporting context |

### Output Schema

`story-planner` returns this structure:

```json
{
  "arc_assessment": "<full synthesized dramatic arc assessment markdown>",
  "overall_score": 83,
  "critic_scores": {
    "audiobook-producer": 84,
    "book-club-moderator": 82,
    "commercial-fiction-editor": 85,
    "literary-fiction-reviewer": 80,
    "publishing-acquisitions-editor": 86,
    "subject-expert": 81
  },
  "verdict": "minor_concerns"
}
```

### Verdict Codes

The synthesized report is normalized to one of three verdict codes:

| Verdict | Meaning |
|--------|---------|
| `strong` | Arc shape is solid; proceed without major concern |
| `minor_concerns` | Arc is viable but has noticeable pacing or payoff weaknesses |
| `significant_issues` | Structural issues are serious enough that the user should consider outline revision |

## Critic Pass

The subagent reuses the existing outline review stack rather than inventing a second scoring system. `critique-runner` returns parsed results for these six critics:

- `audiobook-producer`
- `book-club-moderator`
- `commercial-fiction-editor`
- `literary-fiction-reviewer`
- `publishing-acquisitions-editor`
- `subject-expert`

`story-planner` projects those results into a compact `critic_scores` object and uses the reported `overall_average` as `overall_score`.

## Arc Prompt Set

Phase 2.5 adds three prompts under `prompts/outline_arc/`:

| Prompt | Purpose |
|--------|---------|
| `arc_distribution.md` | Measure dramatic weight distribution across chapters and detect flat or back-loaded structure |
| `promise_payoff.md` | Map narrative promises against later payoff opportunities and identify broken setup chains |
| `arc_synthesis.md` | Merge critic scores and arc analyses into the final structured assessment |

These prompts complement the generic outline critics. They do not replace them.

## Savepoint And State

The feature introduces one new checkpoint and one new story-state field:

| Location | Purpose |
|----------|---------|
| `arc_analysis_complete` savepoint | Persist the synthesized arc assessment after Phase 2.5 completes |
| `arc_assessment` story-state field | Give the orchestrator a stable payload to show at Phase 3 |

The outline itself remains the authoritative input. Phase 2.5 analyzes the existing outline; it does not mutate it.

## Developer Notes

### Key Files

- `.opencode/agents/story-planner.md` — subagent contract and workflow
- `.opencode/skills/narrative-arc/SKILL.md` — output schema, verdict codes, workflow reference
- `prompts/outline_arc/arc_distribution.md` — dramatic-weight prompt
- `prompts/outline_arc/promise_payoff.md` — setup/payoff prompt
- `prompts/outline_arc/arc_synthesis.md` — synthesis prompt
- `.opencode/agents/story-orchestrator.md` — Phase 2.5 integration and Phase 3 presentation rules

### Constraints

- Depth-1 only: no nested subagent dispatch.
- Advisory only: no automated outline rewrite loop.
- Uses finalized outline content explicitly, not a fallback savepoint lookup.
- Keeps returned payload compact so the approval gate stays readable.

## Testing

Phase 2.5 documentation was added after implementation verification on branch `feat/issue-124-story-planner-agent`. Existing test coverage for prompt relocation and story-state interactions continued to pass in the feature branch test run used for PR #130.

## Related

- [Story Orchestrator](./story-orchestrator.md)
- [Comprehensive Manual](../manual.md)
- Issue #124 — Story planner subagent
- PR #130 — Story planner integration