---
description: Resume story generation from the last savepoint
agent: story-orchestrator
---

Resume story generation from the most recent savepoint.

Available stories:
!python3 src/tools/story_state.py --operation list

If a story name was provided ("$1"), resume that story. If no story name was provided (empty "$1"), ask the user which story from the list above they want to continue.

Steps:
1. List savepoints for the chosen story using the savepoint-mgr tool
2. Identify the most recent savepoint
3. Load that savepoint and read the story state
4. Resume the pipeline from where it left off
