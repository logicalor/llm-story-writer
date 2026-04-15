---
description: Create a manual savepoint for the current story
agent: story-orchestrator
---

Create a manual savepoint for the current story.

1. Read the story state to identify the active story name
2. Create a savepoint using the savepoint-mgr tool:
   - If a name was provided ("$1"), use "$1" as the step name
   - If no name was provided (empty "$1"), use "manual_" followed by the current timestamp as the step name
3. Include the current story state as the savepoint data
4. Confirm the savepoint was created successfully
