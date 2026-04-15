---
description: Initialize a new story and start the generation pipeline
agent: story-orchestrator
---

Start a new story using the prompt file at `$1`.

1. Verify the prompt file exists at `$1`. If it does not exist, stop and report the error.
2. Read the prompt file contents — this is the user's creative brief for the story.
3. Begin the full generation pipeline from Phase 1 (initialization) through to completion.
   - Phase 1: Initialize the story (create story directory and state)
   - Phase 4: Initialize the wiki
   - Continue through all remaining phases (outline, chapters, etc.)

The prompt file path is: `$1`
