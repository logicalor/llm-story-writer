---
description: Regenerate a specific chapter or scene
agent: story-orchestrator
---

Regenerate part of the story based on: $ARGUMENTS

Parse the arguments to determine what to regenerate:
- "chapter N" → regenerate chapter N entirely (e.g., "chapter 5")
- "scene C S" → regenerate scene S of chapter C (e.g., "scene 3 2")

Steps:
1. Identify the target story from current state (read story state to find the active story)
2. Identify what to regenerate from the arguments above
3. Check which wiki entities were introduced or modified in the target chapter/scene
4. Consider rolling back wiki entries affected by the content being regenerated
5. Regenerate the content using the existing pipeline (chapter-writer for chapters, scene-writer for scenes)
6. After regeneration, update the wiki with any new or changed entities from the regenerated content
7. Run wiki-lint to verify consistency after the update

If the arguments are unclear, ask the user to clarify using the formats shown above.
