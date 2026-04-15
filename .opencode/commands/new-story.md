---
description: Initialize a new story and start the generation pipeline
agent: story-orchestrator
---

Start a new story using the prompt file at `$1`.

1. Verify the prompt file exists at `$1`. If it does not exist, stop and report the error.
2. Read the prompt file contents — this is the user's creative brief for the story.
3. Begin the full generation pipeline from Phase 1 through to completion. Follow the story-pipeline skill for the correct phase sequence.

The prompt file path is: `$1`
