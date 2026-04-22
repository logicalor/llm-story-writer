# Chapter Outline Expander

> Dedicated Phase 7a subagent that expands all chapter outlines and carries structured continuity forward between chapters.

## Overview

Issue #123 and PR #129 moved the Phase 7a chapter outline expansion loop out of the story orchestrator and into a dedicated `chapter-outline-expander` subagent. This change removes a long-running mutable continuity loop from the orchestrator's working memory and keeps the expansion pass bounded to one tool-only agent.

The subagent runs once after wiki population and before chapter drafting starts. It owns the full expansion pass for chapters 1 through `wanted_chapters`, writes each chapter's expanded outline to story state, and carries continuity forward using two inputs: the rolling `continuitySummary` returned by `outline-generator` and the prior chapter's structured handoff artifact when one exists.

## Pipeline Placement

`chapter-outline-expander` runs in Phase 7a of the story pipeline.

| Step | Runs When | What It Produces |
|------|-----------|------------------|
| Phase 7a | Once per story, before any chapter drafting | `chapters.{N}.expanded_outline` entries and chapter-outline expansion savepoints |
| Phase 7h dependency | After each accepted chapter, on later iterations | Consumes `chapters.{N-1}.handoff` to enrich continuity for the next expansion |

Operationally, this means the orchestrator no longer expands chapter outlines chapter-by-chapter inside its own loop. It dispatches one subagent, waits for expansion to complete, then starts the normal per-chapter drafting flow.

## Inputs And Outputs

### Inputs

The orchestrator dispatches the subagent with a compact contract:

- `story_name` — story state namespace to read and write
- `wanted_chapters` — total number of chapters to expand
- `expand_outline` — skip flag for installations that disable expansion
- `model` — optional model override for `outline-generator`

During the loop, the subagent also reads:

- `chapters.{N-1}.handoff` from story state when a prior chapter handoff exists
- The previous `continuitySummary` returned by `outline-generator`

### Outputs

For each chapter, the subagent writes:

- `chapters.{N}.expanded_outline` — expanded chapter outline used by later drafting phases
- `chapter_outline_expansion/chapter_{N}` savepoint data — progress marker for the expansion pass

At completion it returns a small status object to the orchestrator, such as `complete` or `skipped`.

## Handoff Artifact Relationship

The per-chapter handoff artifact is the developer-facing reason this subagent matters. After each accepted chapter, the orchestrator generates `chapters.{N}.handoff` from the accepted chapter outline using `prompts/chapters/generate_handoff.md`.

That artifact contains five continuity categories:

- `resolved_beats`
- `obligations`
- `active_tensions`
- `timeline`
- `character_deltas`

On the next expansion iteration, `chapter-outline-expander` reads that structured state and prepends it to the continuity input sent to `outline-generator`. Operators should expect later chapter expansions to reflect explicit carry-forward obligations and character-state changes, not only a free-form rolling summary.

## Operator Notes

- If `generation.expand_outline` is `false`, the subagent exits immediately and the pipeline proceeds without expanded outlines.
- This agent is depth-1 only. It calls tools and never dispatches nested subagents.
- Continuity state now survives orchestrator context pressure better because the orchestrator no longer owns the rolling Phase 7a loop.
- The handoff artifact lives in story state, not the wiki. It is continuity-planning data for expansion, not reader-facing story memory.

## Key Files

| File | Purpose |
|------|---------|
| `.opencode/agents/chapter-outline-expander.md` | Subagent workflow, tool contract, continuity threading rules |
| `.opencode/agents/story-orchestrator.md` | Parent orchestration logic for Phase 7a dispatch and Phase 7h handoff generation |
| `prompts/chapters/generate_handoff.md` | Prompt template for the structured handoff JSON artifact |
| `.opencode/skills/story-pipeline/SKILL.md` | Pipeline reference updated with the new Phase 7a subagent |

## Related

- [Story Orchestrator](./story-orchestrator.md) — parent pipeline and per-chapter loop placement
- [Tools Reference](../tools.md) — deterministic tools used by the subagent and orchestrator
- [ADR 001: Hybrid Agent-Tool Architecture](../planning/adr/001-hybrid-agent-tool-architecture.md) — depth-1 delegation rule
- Issue #123 — implementation request for Phase 7a extraction and handoff artifact
- PR #129 — implementation of `chapter-outline-expander` and chapter handoff storage
