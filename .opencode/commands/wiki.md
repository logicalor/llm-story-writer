---
description: Show wiki summary and health status
---

Show wiki summary and health status for the story.

Available stories:
!python3 src/tools/story_state.py --operation list

Wiki page count:
!find "stories/$1/wiki" -name "*.md" -not -name "_*" | wc -l

Wiki subdirectories:
!ls -la "stories/$1/wiki/"

Wiki lint results:
!python3 src/tools/wiki_lint.py --operation check-full --name "$1"

Note: The shell commands above will fail if no story name was provided. Handle errors from these commands gracefully.

Format the output as a wiki health report including:
- Total number of wiki pages
- Page counts per subdirectory (characters, locations, events, factions, items, plot-threads, world-rules, themes, relationships, timeline, chapters)
- Last update timestamps from the directory listing
- Any issues or warnings from the lint results

If no story name was provided (empty "$1"), show the list of available stories and ask the user which one they want wiki status for.
