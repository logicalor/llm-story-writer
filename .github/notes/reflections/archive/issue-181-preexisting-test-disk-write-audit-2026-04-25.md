---
date: "2026-04-25"
issue: 181
pr: 192
category: agent
targets:
  - ".github/agents/test-writer.agent.md"
severity: minor
status: archived
---

## Pre-existing tests miss STORIES_DIR patch after disk write added to existing code path

### Finding

PR #192 added disk write logic (assembly output) to an existing orchestrator code path. The three
new tests for the assembly step correctly patched both `presentation.orchestrator.STORIES_DIR` and
`tools._io.STORIES_DIR`. However, the review found that two pre-existing orchestrator tests
(`test_run_pipeline_chapter_revision` and `test_run_pipeline_outline_rejection`) did not include
the `STORIES_DIR` patch. These tests were written before assembly was added to the pipeline and
had never needed the patch — until now.

### Observation

This is a distinct pattern from "savepoint migration test setup" (issue #180): that pattern is
about test fixtures using the wrong data source. This pattern is about an existing test that passes
today but will silently write to real disk (or fail on path resolution) after new disk I/O is added
to the code path it exercises.

When a code change adds a disk write to an existing function, the risk is not only that new tests
need the patch — all pre-existing tests of that function must be audited to confirm they still route
I/O to a temp directory. Missing patches cause test pollution (writes to the live `stories/`
directory), non-deterministic failures when tests run in parallel, or environment-dependent
failures in CI.

### Suggested Improvement

Add a note to `test-writer.agent.md` in the "Write Tests" section:

**"Pre-existing test disk-write audit"** — When implementing code that adds disk writes (file
creation, directory creation, `write_text()`, `mkdir()`, etc.) to a function that already has
test coverage, open every existing test of that function and verify each one patches the relevant
base path constant. A test written before the disk write existed will not have the patch and will
silently write to real storage or fail in CI.

### Action Taken

Applied: Added "Pre-existing test disk-write audit" bullet to `test-writer.agent.md` under
"Write Tests" section.
