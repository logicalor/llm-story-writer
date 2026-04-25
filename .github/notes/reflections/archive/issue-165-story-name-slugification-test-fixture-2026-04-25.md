---
date: "2026-04-25"
issue: 165
pr: 176
category: instruction
targets:
  - ".github/notes/gotchas.md"
severity: minor
status: archived
---

## E2E test story names must be pre-normalized kebab-case

### Finding

During PR #176, the test defined `STORY_NAME = "e2e_test_"` with a comment stating the
pipeline would slugify it to `"e2e-test"`. It then seeded `stories/e2e-test/state.json` and
asserted savepoints under `stories/e2e-test/savepoints/`. The subprocess passed
`--story e2e_test_` to the CLI.

In `run_pipeline()` (orchestrator.py), the pipeline calls
`_validate_story_name(story_name, STORIES_DIR)` but **discards the return value**. The raw
`story_name` is stored in `PipelineState` and used for all subsequent path operations.
All output went to `stories/e2e_test_/`, not `stories/e2e-test/`. The test either failed
(FileNotFoundError on seeded state.json) or passed vacuously against stale data. Only GPT
identified this critical bug; Claude and Gemini missed it.

### Observation

The orchestrator's `run_pipeline()` not propagating the normalized name is a latent design flaw
(Option B fix: capture the return value). But even if that is fixed, the lesson for test authors
is clear: test fixtures should never rely on path normalization side-effects happening inside the
SUT. Using a name that is already in canonical form is defensive and explicit about intent.

### Suggested Improvement

Add gotcha #027 to `gotchas.md` documenting this pitfall for E2E integration test authors. The
gotcha should cover: (1) always use a pre-normalized kebab-case story name in E2E tests, (2)
why the orchestrator does not propagate the normalized name, and (3) how to use `tmp_path` +
`STORIES_DIR` env var for full isolation.

### Action Taken

Applied: added gotcha #027 to `.github/notes/gotchas.md` under the Testing section.
