# Code Review — feat/issue-92-wiki-read-error-path-integration-tests

**Date:** 2026-04-17
**Reviewer:** Claude (raw)
**Branch:** `feat/issue-92-wiki-read-error-path-integration-tests`
**Commit:** `e2549c4 test(integration): add wiki_read error-path integration tests (#92)`

---

## Review Summary

This PR adds three integration tests covering the error paths of `wiki_read.py`: reading a nonexistent slug from an existing wiki, calling `match-entities` when the wiki directory is absent, and reading from an empty wiki directory. All three tests produce the expected empty-success responses and pass cleanly. The change is well-scoped and follows project conventions throughout.

**Files Reviewed:** 1
**Findings:** 0 Critical, 1 Warning, 1 Suggestion

---

## Phase 1 — Structural Review

- **Commit message:** `test(integration): add wiki_read error-path integration tests (#92)` — correct type prefix, references issue number. Passes.
- **Branch name:** `feat/issue-92-wiki-read-error-path-integration-tests` — follows `feat/issue-N-...` convention. Passes.
- **Scope:** 118 lines, single new test file. Small and focused. Passes.
- **Unrelated changes:** None. All changes relate solely to the stated purpose.
- **Numbered step lists:** No agent or skill files modified. Not applicable.
- **File relocation:** No files moved or renamed. Not applicable.
- **Sibling item orphaning:** No sections removed. Not applicable.
- **Stale prose counts:** No counts affected. Not applicable.
- **`tools:` array coupling:** No agent or tool registrations changed. Not applicable.
- **Model-specific variant sync:** No agent files modified. Not applicable.
- **Section heading drift:** No documentation modified. Not applicable.
- **YAML frontmatter:** No frontmatter sections removed. Not applicable.
- **Agent `model:` field format:** No agent files created or edited. Not applicable.
- **Shell snippet safety:** No shell snippets in agents or skills. Not applicable.

---

## Phase 2 — Code Review

The test helper design is clean. `_make_env`, `_run_tool`, and `_assert_success` are module-level utilities following the same pattern as other integration tests in this project.

`PROJECT_ROOT` and `WIKI_READ_SCRIPT` are resolved at module level via `Path(__file__).resolve().parents[2]`, which is the correct approach for a file two levels deep in `tests/integration/`.

`{**os.environ}` correctly inherits the parent environment so the subprocess can resolve Python imports, system paths, etc. This is standard practice for subprocess-based integration tests.

`_assert_success` truncates stdout/stderr to 500 characters in the assertion message — an appropriate guard against flooding test output on failure.

The JSON parsing in `_assert_success` handles the `indent=2` output from `wiki_read.py` correctly, since `json.loads` is indentation-agnostic.

`test_read_nonexistent_slug` deliberately creates an existing page file before invoking the tool with a different slug. This is intentional and correct — it distinguishes "slug not found in a non-empty wiki" from "wiki is empty", which is a distinct scenario already covered by `test_read_empty_wiki_dir`. The setup is justified.

No violations of project conventions (snake_case naming, stdlib → third-party → local import ordering, proper use of `from __future__ import annotations`).

---

## Phase 3 — Frontend Review

Not applicable. No frontend changes.

---

## Phase 4 — Security Review

- **Subprocess injection:** `subprocess.run` uses a list (`[sys.executable, str(script), *args]`) rather than `shell=True`. No injection risk.
- **Environment inheritance:** `{**os.environ}` passes the full parent environment to the subprocess. This is appropriate for test code that needs the host environment (PATH, HOME, Python resolver) and carries no production security risk.
- **No hardcoded credentials or API keys.**
- **No user-supplied input in subprocess args** — all arguments are test-constructed constants.

---

## Phase 5 — Testing Review

All three tests pass (verified by running `pytest tests/integration/test_wiki_read_integration.py -v` — 3 passed in 0.14s).

The three scenarios map directly to the three early-exit branches in `wiki_read.py`:

| Branch in implementation | Test covering it |
|---|---|
| `cmd_read`: wiki dir does not exist | `test_read_empty_wiki_dir` (via wiki dir existing but empty) |
| `cmd_read`: `find_pages` returns empty list | `test_read_nonexistent_slug` |
| `cmd_match_entities`: wiki dir does not exist | `test_match_entities_no_wiki` |

One untested branch exists: the `if not args.text` guard in `cmd_match_entities` (lines 82–84 of `wiki_read.py`) which writes an error to stderr and calls `sys.exit(2)`. This exits with a non-zero return code, meaning `_assert_success` would catch it as a failure — but the absence of a test for this path means the guard is not integration-tested. This is a minor omission.

---

## Phase 6 — Performance Review

The only performance-relevant parameter is `timeout=300` (5 minutes) set as the default for `_run_tool`. Functional tests that spawn a trivial Python subprocess complete in milliseconds; a 5-minute timeout is 300× too generous and will significantly delay detection of hung or deadlocked processes in CI. Other integration tests in this project use similar generous timeouts (this appears to be a project-wide pattern), so this is a Warning rather than a convention violation.

---

## Phase 7 — Documentation Review

- Module-level docstring is present and accurate: `"""Integration tests for wiki_read error-path behavior."""`
- No README or ADR updates are required for test-only changes.
- No inline documentation issues.

---

## Findings

### Warning Findings

```
[W-01] Subprocess timeout is excessively generous
Category: Performance
Severity: Warning
File: tests/integration/test_wiki_read_integration.py
Lines: 27 (default value in _run_tool signature)
Description: timeout=300 (5 minutes) is the default for all subprocess calls in this
  test file. Each test spawns a trivial Python script that completes in milliseconds.
  A 5-minute timeout means a hung subprocess will not be detected for 5 minutes,
  significantly slowing CI pipelines in failure scenarios. A value of 30 seconds
  would be more than adequate and fail faster.
Suggestion: Change the default to timeout: int = 30 in the _run_tool signature.
```

### Suggestions

```
[S-01] The --text required-guard branch in cmd_match_entities is not integration-tested
Category: Testing
Severity: Suggestion
File: tests/integration/test_wiki_read_integration.py
Lines: general
Description: wiki_read.py lines 82–84 check `if not args.text` and call sys.exit(2)
  with a non-zero exit code. This error path is not covered by any test in this file.
  While it is a CLI validation guard rather than a domain logic path, integration
  coverage of it would be consistent with the stated "error-path" scope of the PR.
Suggestion: Add a test that invokes the tool with --operation match-entities and
  --name test-story but omits --text, and asserts that returncode == 2 and that
  stderr contains the expected error message.
```

---

## Overall Assessment

The PR is ready to merge. It is a clean, focused test addition with no production code changes, no security issues, and conventions followed throughout. The three tests correctly exercise the main error paths in `wiki_read.py` and all pass. The one Warning (excessive subprocess timeout) is a minor quality issue consistent with the project's existing integration test patterns; the one Suggestion (missing `--text` guard test) is a low-priority addition that falls outside the minimum required coverage for this scope. Neither blocks merge.
