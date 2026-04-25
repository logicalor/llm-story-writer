Resume story generation from the most recent savepoint.

Available stories:
!python3 src/tools/story_state.py --operation list

If a story name was provided ("$1"), resume that story. If no story name was provided (empty "$1"), ask the user which story from the list above they want to continue.

Steps:
1. Call `savepoint-mgr` (operation: `next-phase`, name: chosen story name) — this returns a deterministic resume target. The output JSON contains `last_completed` (the highest-completed savepoint) and `next_phase` (the human-readable description of where to resume). Do NOT use `list` and reason about ordering yourself; the canonical phase walk is owned by the tool.
2. Read story state via `story-state` (operation: `read`, name: story name) for context (config values, story_name, prompt metadata, chapter counts).
3. If `missing_below_top` is non-empty in the response, log a warning that intermediate savepoints are missing — but proceed with resume from `next_phase` regardless. Missing intermediate savepoints indicate procedural drift in an earlier run, not a blocker.
4. Resume the pipeline from `next_phase` as returned by the tool. Follow the `story-pipeline` skill for the phase definition.

**CRITICAL — unattended resume, no stopping between phases:**

- `/continue` is an **unattended batch resume**. There is no human available to answer prompts between phases. Treat the entire run as a single uninterrupted session.
- **Do not stop after narrating the plan.** Immediately in the same turn, dispatch the first subagent or tool call required by `next_phase`. Narrating "Starting expansion..." or "Dispatching X..." is **not** a dispatch — you must actually emit the tool/task call.
- **Do not stop when a subagent returns.** A subagent response ends that subagent's turn, not the orchestrator's. The moment you receive a subagent's result, continue immediately with the next phase, chapter, or tool call in the pipeline in the same turn. Do not summarise progress, do not ask for confirmation, do not wait.
- **Do not stop between chapters.** After `chapter_{N}_complete` is written, immediately begin Phase 7b for chapter `N+1` in the same turn until `N == wanted_chapters`.
- **Only stop when:**
  1. The pipeline reaches completion (`story_complete` and, if applicable, `final_edit_complete` are written), **or**
  2. A tool or subagent returns an unrecoverable error after a retry, **or**
  3. The `interactive` config flag is `true` and the pipeline reaches an explicit approval gate (Phase 3 outline approval). In batch mode (the default for `/continue`), there are no approval gates.
- If you find yourself about to end your turn for any other reason — a subagent finished, a savepoint was written, a phase completed — that is the signal to **keep going**, not to stop.

Failure to drive the pipeline to completion in a single `/continue` turn is a workflow defect.