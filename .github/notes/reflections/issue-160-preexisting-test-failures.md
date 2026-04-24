---
date: "2026-04-24"
issue: 160
pr: 170
category: instruction
targets:
  - ".github/notes/deferred.md"
severity: minor
status: active
---

## Pre-existing test failures in `test_story_state_tool.py` and `test_wiki_extract_tool.py`

### Finding

During PR #170 testing, 19 pre-existing failures were observed in `tests/unit/test_story_state_tool.py` and `tests/unit/test_wiki_extract_tool.py`. These failures existed on the development branch before the PR was merged and are unrelated to the pipeline primitives implementation. No reviewer flagged them as a blocker; they were explicitly noted as "pre-existing" and excluded from the PR assessment.

### Observation

Pre-existing failures in the test suite create noise that makes it harder to confirm clean baselines. Reviewers must mentally filter out known-broken tests in each PR, which is error-prone. If left unresolved, these failures can mask genuine regressions introduced by new PRs.

These are likely caused by stale mocks, missing test fixtures, or API changes that were not back-propagated to these test files.

### Suggested Improvement

Record in `deferred.md` so the failures are tracked and can be addressed in a dedicated cleanup issue rather than accumulating silently.

### Action Taken

Applied: added entry to `.github/notes/deferred.md` tracking the 19 pre-existing failures for future cleanup.
