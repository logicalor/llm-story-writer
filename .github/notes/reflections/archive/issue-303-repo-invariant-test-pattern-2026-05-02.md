---
date: "2026-05-02"
issue: 303
pr: 315
category: agent
targets:
  - ".opencode/agents/test-writer.md"
severity: minor
---

## Repo-invariant tests as a cleanup-issue companion

### Finding

Issue #303 (PR #315) retired 11 dead `GenerationSettings` fields and 4 orphan prompt files.
Alongside the deletion, `tests/unit/test_repo_invariants.py` was added containing two structural tests:

1. `test_no_dead_generation_settings` — scans the GenerationSettings domain object and asserts
   every declared field is referenced in at least one active code path.
2. `test_no_orphan_prompts` — scans `prompts/` and asserts every `.md` file outside `_unused/`
   is referenced somewhere in `src/` or `prompts/agents/`.

These tests verify structural properties of the codebase itself — not runtime behaviour — and
prevent future re-accumulation of the exact categories of dead code that were cleaned up.

### Observation

The Test Writer currently has no guidance for repo-invariant tests as a test category. All existing
guidance targets functional/behavioural patterns (happy path, error path, LLM parse failures,
integration boundaries). Without explicit mention of repo-invariant tests, a Test Writer dispatched
for a cleanup issue may not include them, leaving the cleaned state unguarded and allowing the same
dead code or orphan files to accumulate again in future PRs.

Repo-invariant tests are a distinct category with distinct characteristics:
- They test structural properties of the workspace, not runtime function behaviour
- They use `pathlib`, `ast`, or text-scanning — not mocked collaborators
- They belong in `tests/unit/test_repo_invariants.py`
- Their primary value is regression prevention, not defect detection

### Suggested Improvement

Add a guidance bullet to the Step 2 "Write Tests" section of `test-writer.md` explaining the
repo-invariant test pattern and when to write them.

> **Repo-invariant tests (cleanup issues):** When your dispatch is a cleanup issue that removes
> dead fields, dead code, or orphan files, include at least one repo-invariant test that guards
> the cleaned state going forward. Repo-invariant tests scan workspace files using `pathlib`,
> `ast`, or `grep`-equivalent patterns, and assert structural properties that must remain true —
> e.g., no `.md` files in `prompts/` (outside `_unused/`) are unreferenced, no fields in a
> domain settings class are declared but never read. Place these tests in
> `tests/unit/test_repo_invariants.py`. They use no mocks and scan the real workspace, which
> makes them sensitive to new violations immediately on any future PR.
> (Source: issue #303, PR #315.)

### Action Taken

Applied: added "Repo-invariant tests (cleanup issues)" guidance bullet to Step 2 of
`.opencode/agents/test-writer.md`, after the "Advisory pipeline phases" bullet and before the
"After writing each test..." prompt.
