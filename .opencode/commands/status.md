---
description: Show story generation progress
---

Show a formatted progress summary for the story.

Available stories:
!python3 src/tools/story_state.py --operation list

Story details:
!python3 src/tools/story_state.py --operation read --name "$1"

Savepoints:
!python3 src/tools/savepoint_manager.py --operation list --name "$1"

Wiki pages:
!find "stories/$1/wiki" -name "*.md" -not -name "_*" -not -name "index.md" -not -name "log.md" -not -name "contradictions.md" | head -50

Note: The shell commands above will fail if no story name was provided. Handle errors from these commands gracefully.

Format the output as a human-readable progress summary including:
- Story name and creative direction
- Chapters completed vs total planned
- Current pipeline phase (derived from the most recent savepoint name)
- Wiki statistics — page counts by subdirectory (characters, locations, events, etc.)

If no story name was provided (empty "$1"), show the list of available stories and ask the user which one they want status for.
