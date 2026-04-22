---
name: narrative-arc
description: Narrative arc analysis data structures - assessment output schema, critic score format, verdict codes, and workflow reference for story-planner.
version: 1.0.0
---

# Narrative Arc Skill

Reference for the post-outline dramatic arc analysis flow used by `story-planner`.

---

## Workflow Overview

The `story-planner` workflow runs in this order:

1. Read the final outline and `story_elements` from `story-state`
2. Run the 6 outline critics through `critique-runner`
3. Generate arc distribution analysis from `prompts/outline_arc/arc_distribution`
4. Generate promise/payoff analysis from `prompts/outline_arc/promise_payoff`
5. Synthesize the final assessment from `prompts/outline_arc/arc_synthesis`
6. Save the assessment to the `arc_analysis_complete` savepoint

This workflow is advisory only. It does not trigger an automated outline revision loop.

---

## Assessment Output Schema

The subagent returns this structure to the orchestrator:

```json
{
  "arc_assessment": "<full dramatic arc assessment markdown>",
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

### Field Definitions

| Field | Type | Description |
|-------|------|-------------|
| `arc_assessment` | string | Full synthesized dramatic arc assessment in Markdown |
| `overall_score` | number | Numeric overall average from the 6 outline critics |
| `critic_scores` | object | Per-critic numeric score keyed by critic name |
| `verdict` | string | Normalized verdict code derived from the final assessment |

---

## Critic Score Format

`critique-runner` returns parsed outline critic data under `critic_results` and `overall_average`.

Expected critic set:
- `audiobook-producer`
- `book-club-moderator`
- `commercial-fiction-editor`
- `literary-fiction-reviewer`
- `publishing-acquisitions-editor`
- `subject-expert`

`critic_scores` is the compact projection of those results into a single dictionary of critic name -> numeric score.

---

## Verdict Codes

Allowed normalized verdict codes:
- `strong`
- `minor_concerns`
- `significant_issues`

These map from the final assessment's `Reviewer Verdict` line.

---

## Savepoint

The final synthesized assessment is persisted under this savepoint:
- `arc_analysis_complete`

---

## Prompt Location

Arc analysis prompts live here:
- `prompts/outline_arc/`

---

## Related Reference

For the outline JSON structure consumed by this workflow, see `.opencode/skills/outline-structure/SKILL.md`.