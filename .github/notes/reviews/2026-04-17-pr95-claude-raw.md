# Code Review Report — PR #95 (feat/issue-94-wiki-read-cli-validation-tests)

**Reviewer:** Claude Sonnet 4.6  
**Date:** 2026-04-17  
**Branch:** `feat/issue-94-wiki-read-cli-validation-tests`  
**Base:** `development`

---

## Review Summary

This PR adds two integration tests to `TestWikiReadCLIValidation` covering CLI argument validation error paths in `wiki_read.py`: missing `--text` for `match-entities` and an invalid `--operation` value. The scope is minimal (29 lines added to a single test file) and the new tests align correctly with the implementation's behavior. A few minor style issues are noted; no critical findings.

**Files Reviewed:** 1  
**Findings:** 0 Critical, 1 Warning, 2 Suggestion

---

## Findings

### Warning Findings

```
[W-01] `feat/` branch prefix used for a test-only change
Category: Style
Severity: Warning
File: (branch name)
Lines: general
Description: The branch is named `feat/issue-94-...` but contains only test additions.
  Project convention maps `feat:` to production feature work. A test-only
  PR should use a `test/` branch prefix to keep the commit history and
  branch taxonomy consistent.
Suggestion: Rename branch to `test/issue-94-wiki-read-cli-validation-tests` for
  future PRs of this type.
```

---

### Suggestions

```
[S-01] Dead filesystem setup in `test_match_entities_missing_text`
Category: Style
Severity: Suggestion
File: tests/integration/test_wiki_read_integration.py
Lines: 123-125
Description: `(stories_dir / "test-story").mkdir(parents=True)` creates a real
  directory that is never accessed during this test. `cmd_match_entities`
  performs the `if not args.text` guard before calling `_validate_story_name`,
  so the missing story directory would cause no test interference either
  way. The mkdir is harmless but is dead code in this scenario.
Suggestion: Remove the `mkdir` call (and the two path assignments if nothing else
  uses them) to keep the test minimal and make the isolation intent obvious.
  If keeping them for symmetry with other test methods, a brief comment
  noting they are not exercised here would reduce confusion.
```

```
[S-02] `test_invalid_operation` makes no stderr assertion
Category: Testing
Severity: Suggestion
File: tests/integration/test_wiki_read_integration.py
Lines: 144-147
Description: The test verifies `returncode != 0` but does not assert anything about
  stderr content. For `test_match_entities_missing_text` the error text is
  checked, so the pattern is inconsistent. argparse writes something like
  "argument --operation: invalid choice: 'invalid-value' (choose from 'read',
  'match-entities')" to stderr, which is specific enough to assert against.
Suggestion: Add `assert "invalid-value" in result.stderr or "invalid choice" in
  result.stderr` to make the test document the expected error message and
  guard against a future change that exits non-zero for a different reason.
```

---

## Phase-by-Phase Notes

### Phase 1 — Structural

- Commit message follows convention and references the issue number. ✓
- Branch name uses `feat/` for test-only work (flagged as W-01).
- Scope is 29 lines; well within acceptable limits.
- All changes are scoped to the stated purpose; no unrelated modifications.
- No agent/skill files, no numbered step lists, no file relocations, no prose counts affected.
- The existing missing end-of-file newline on the last line of the pre-existing test class is corrected incidentally by this PR. ✓

### Phase 2 — Code

- New tests use the same `_run_tool` / `_make_env` helpers as existing tests. ✓
- Class name `TestWikiReadCLIValidation` is clear and follows the `Test<Subject><Aspect>` naming pattern. ✓
- Both new tests follow the arrange/act/assert structure. ✓

### Phase 4 — Security

- Tests invoke `wiki_read.py` via subprocess with a fully isolated `tmp_path` environment. No user-controlled input surfaces. No credentials or secrets in the test code. ✓

### Phase 5 — Testing

- `test_match_entities_missing_text`: asserts non-zero exit and that stderr contains `"--text"` or `"required"`. The implementation writes `"Error: --text is required for match-entities"` to stderr, which contains both target strings. Assertion is correct and specific. ✓
- `test_invalid_operation`: asserts non-zero exit only. argparse `choices` validation will reject `"invalid-value"` with exit code 2. The assertion is logically correct but under-specified (S-02).
- Verified against implementation: argparse declares `choices=["read", "match-entities"]` at line 106 of `wiki_read.py`; `cmd_match_entities` checks `if not args.text` and calls `sys.exit(2)` at line 84. Both behaviors match the test assertions. ✓
- No tests for `--text ""` (empty string), but that gap pre-dates this PR and is not a regression.

### Phase 6 — Performance

No performance considerations for this test-only PR.

### Phase 7 — Documentation

No documentation changes needed for a test-only addition.

---

## Overall Assessment

The PR is ready to merge with no blocking issues. The two new tests are correct, properly isolated, and verify real behavior against the actual `wiki_read.py` implementation. The branch naming convention mismatch (W-01) is a minor process note for future work. The two suggestions (S-01, S-02) would marginally improve test clarity and consistency but are not required before merge.
