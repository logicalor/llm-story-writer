---
date: "2026-04-22"
issue: 124
pr: 130
category: skill
targets:
  - ".opencode/skills/story-pipeline/SKILL.md"
severity: minor
status: archived
---

<!-- Archived. Full note in archive/issue-124-subagent-savepoint-ownership-2026-04-22.md -->

## Subagents creating savepoints — orchestrator ownership rule undocumented

### Finding

During PR #130, `story-planner.md` Step 6 called `savepoint-mgr (operation: save, step: arc_analysis_complete, data: arc_assessment)` to checkpoint its output. The `story-orchestrator` Phase 2.5 independently created the same savepoint. Because `savepoint-mgr` overwrites existing entries, the orchestrator's write (which contained minimal or no payload) overwrote the subagent's richer arc assessment snapshot. Claude and Gemini flagged this as a majority warning (M-W-01); the fix was to remove the savepoint call from `story-planner` entirely and let the orchestrator own the checkpoint.

No authoritative rule documents this ownership boundary. The `story-pipeline/SKILL.md` describes what each phase's savepoint is named and when it is created — but nowhere states that subagents must not call `savepoint-mgr` directly. Without this rule, a Coder implementing a new subagent has no guidance that creating its own savepoint is wrong; it appears to be a reasonable pattern for checkpointing work.

### Observation

The architectural constraint is clear: the orchestrator drives the pipeline and owns all state persistence. Subagents are delegates — they perform compute, write intermediate results to `story-state`, and return. The orchestrator decides when and what to checkpoint, after confirming the subagent's results are fully stored. Subagent-created savepoints create a race condition: the orchestrator then overwrites with a shallower payload.

The story-pipeline SKILL is the natural home for this rule — it is the authoritative reference that both the Coder and orchestrator load when working with the pipeline. Adding a "Savepoint Ownership" section after the Subagents table makes the constraint discoverable at the right reading moment.

### Suggested Improvement

**`story-pipeline/SKILL.md` — add a Savepoint Ownership section after the subagent constraint sentence:**

```markdown
## Savepoint Ownership

**The orchestrator owns the savepoint lifecycle. Subagents must never call `savepoint-mgr` directly.**

- Savepoints are checkpoints created by `story-orchestrator` at the boundary of each phase — not by subagents during their internal work.
- When a subagent completes its delegated work, it writes results to `story-state` (or produces handoff artifacts) and returns to the orchestrator. The orchestrator then creates the savepoint after confirming results are stored.
- **Why this matters:** If a subagent creates its own savepoint and the orchestrator also creates one at the same step name, the orchestrator's write silently overwrites the subagent's richer payload (`savepoint-mgr` overwrites existing entries by default). A pipeline resumed from that savepoint recovers a degraded snapshot.
- **Correct pattern:** `story-orchestrator` Phase 2.5 creates `arc_analysis_complete` with the full arc payload after `story-planner` returns. `story-planner` writes only to `story-state` — it never calls `savepoint-mgr`.
```

### Action Taken

Applied: Added Savepoint Ownership section to `.opencode/skills/story-pipeline/SKILL.md` immediately after the subagent constraint sentence and the horizontal rule, before the Quality Gates section.
