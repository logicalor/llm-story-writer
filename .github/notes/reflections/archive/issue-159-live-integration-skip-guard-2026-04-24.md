---
date: "2026-04-24"
issue: 159
pr: 168
category: instruction
targets:
  - ".github/agents/_shared/review-checklist.md"
severity: minor
status: archived
---

## Live integration tests missing suite-standard skip guard

### Finding

`tests/integration/test_openai_async_provider_live.py` was committed without the `llm_available` fixture from `tests/integration/conftest.py`. This fixture is the suite-standard mechanism for skipping live tests when no local LLM endpoint is running. All three reviewers flagged this independently (U-W-01 in the synthesis). Every other integration test in the suite skips cleanly under `pytest tests/integration/` on an unprovisioned machine; the new test hard-fails instead.

The `pyproject.toml` default test run is scoped to `tests/unit/`, which does insulate bare `pytest` from the issue — but it is not the only invocation context. Developers running `pytest tests/`, `pytest tests/integration/`, or any CI stage that exercises the integration directory will encounter a hard failure rather than a graceful skip.

### Observation

There is no explicit review checklist item requiring live integration tests to carry a skip guard. Phase 5 (Testing) checks for coverage, conventions, and assertion quality, but does not specifically prompt reviewers to verify that tests requiring external services carry service-availability guards. The existing pattern is well-established in the codebase, but relies on reviewers recognising the filename pattern (`test_*_live.py`) and recalling the convention without a checklist prompt.

### Suggested Improvement

Add a bullet to Phase 5 (Testing) in the review checklist explicitly covering live test skip guards.

### Action Taken

Applied: added "Live test skip guards" checklist item to Phase 5 in `.github/agents/_shared/review-checklist.md`.
