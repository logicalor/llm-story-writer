---
date: "2026-04-25"
issue: 161
pr: 171
category: instruction
targets:
  - ".github/notes/gotchas.md"
severity: minor
status: archived
---

## Story state file is `state.json` — not `story_state.json`

### Finding

PR #171's `_load_story_prompt()` in `src/presentation/orchestrator.py` constructed the path
`story_state.json` to load the story concept from disk. Filesystem verification confirmed that
all existing story directories (`stories/test_story/`, `stories/test-story/`,
`stories/the-silence-between-stars/`) store state in `state.json` — none contain
`story_state.json`. Because the function silently returns `""` on a missing file, the pipeline
produced an empty story prompt for every pre-existing story with no error signal.

Identified by GPT as a Critical finding (C-01) in the Synthesized Review; downgraded to Warning
because the function degrades gracefully rather than crashing. Not detected by Claude or Gemini.

### Observation

`story_state.json` is a plausible filename but contradicts the actual on-disk convention. Any new
module that reads story state without examining an existing story directory is at risk of repeating
this mistake. The silent empty-string fallback common in file-loading functions amplifies the risk
by making the mismatch invisible until downstream phases fail with no trace of the root cause.

### Suggested Improvement

Add gotcha entry #016 to `.github/notes/gotchas.md` under a new `## Story Storage` section
documenting the `state.json` filename convention.

### Action Taken

Applied: Added gotcha entry #016 (`gotcha-story-state-filename-convention-016`) to
`.github/notes/gotchas.md` under `## Story Storage`.
