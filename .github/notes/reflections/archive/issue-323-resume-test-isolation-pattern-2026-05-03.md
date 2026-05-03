---
date: "2026-05-03"
issue: 323
pr: 335
category: agent
targets:
  - ".opencode/agents/test-writer.md"
severity: minor
---

## Interrupt+Resume Integration Test Isolation Pattern

### Finding

`test_resume_granularity.py` (issue #323, PR #335) establishes a concrete pattern for
interrupt+resume integration tests that is not yet documented in `test-writer.md`. The
pattern has four specific requirements that are non-obvious:

1. Use a `contextmanager` (`_patched_pipeline`) to bundle all agent patches, `STORIES_DIR`
   patches, and async mock wiring together into a single reusable fixture.
2. Use **different story names** (`"baseline-story"`, `"resume-story"`) within the same
   `tmp_path` — shared names cause savepoint collisions between runs.
3. Write chapter disk files **before** calling `_write_savepoint` — the resume logic reads
   from disk, so the file must exist at the point the savepoint is written.
4. `_write_savepoint` is directly importable from `presentation.orchestrator` as a test hook
   for pre-writing partial pipeline state.

### Observation

Without this guidance, a future test writer building interrupt+resume tests would likely:
share story names (causing savepoint collisions), write the savepoint before disk files
(causing resume failure on missing chapter content), or not know `_write_savepoint` is
importable. These failure modes produce confusing, non-deterministic test failures rather
than clear assertion errors.

### Suggested Improvement

Add a bullet to `.opencode/agents/test-writer.md` documenting the interrupt+resume test
isolation pattern, placed after the "Repo-invariant tests" bullet.

### Action Taken

Applied: Added "**Interrupt+resume integration test isolation:**" bullet to
`.opencode/agents/test-writer.md` after the "Repo-invariant tests" bullet.
