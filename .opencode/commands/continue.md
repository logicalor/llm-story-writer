---
description: Resume story generation from the last savepoint
agent: story-orchestrator
---

Resume story generation from the most recent savepoint.

Available stories:
!python3 src/tools/story_state.py --operation list

If a story name was provided ("$1"), resume that story. If no story name was provided (empty "$1"), ask the user which story from the list above they want to continue.

Steps:
1. Call `savepoint-mgr` (operation: `next-phase`, name: chosen story name) — this returns a deterministic resume target. The output JSON contains `last_completed` (the highest-completed savepoint) and `next_phase` (the human-readable description of where to resume). Do NOT use `list` and reason about ordering yourself; the canonical phase walk is owned by the tool.
2. Read story state via `story-state` (operation: `read`, name: story name) for context (config values, story_name, prompt metadata, chapter counts).
3. If `missing_below_top` is non-empty in the response, log a warning that intermediate savepoints are missing — but proceed with resume from `next_phase` regardless. Missing intermediate savepoints indicate procedural drift in an earlier run, not a blocker.
4. Resume the pipeline from `next_phase` as returned by the tool. Follow the `story-pipeline` skill for the phase definition.

**CRITICAL: Do not stop after narrating the plan.** Immediately in the same turn, dispatch the first subagent or tool call required by `next_phase` without waiting for user confirmation. Narrating "Starting expansion..." or "Dispatching X..." is not a dispatch — you must actually emit the tool/task call. The `/continue` command is an unattended resume; no human input is available between phases.
