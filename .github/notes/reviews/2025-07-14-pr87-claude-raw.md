# Code Review Report — PR #87 (feat/issue-27-e2e-integration-test-with-wiki)

**Branch:** `feat/issue-27-e2e-integration-test-with-wiki`
**Reviewed against:** `development`
**Date:** 2025-07-14
**Reviewer:** Claude Sonnet 4.6

---

## Review Summary

This PR delivers the first end-to-end integration test suite for the full story generation pipeline with wiki support, covering all 10+ tool invocations from story-state init through final assembly. The architecture of the session-scoped fixture is sound and the test assertions are well-matched to the implementation. However, a critical bug in the character wiki-creation block will cause the entire session-scoped fixture to fail before any chapter is generated: `--confidence` is passed without a value, causing argparse to exit with code 2. All 12 tests will fail as a result. Additionally, three script-level constants are defined but never referenced, one of which represents a gap in test coverage (`WIKI_READ_SCRIPT`). The agent file carry-over changes are correct — all model fields are valid scalar strings and all three model-specific variants remain in sync within each family.

**Files Reviewed:** 31 (24 agent files, 3 integration test files, pyproject.toml, docs/testing/integration-tests.md, README.md, docs/README.md)
**Findings:** 1 Critical, 6 Warning, 3 Suggestion

---

## Findings

### Critical Findings

```
[C-01] Missing --confidence value for character wiki page creation
Category: Correctness
Severity: Critical
File: tests/integration/test_e2e_opencode.py
Lines: 265-284
Description: The character creation loop passes `--confidence` with no value, immediately
followed by `--first-appearance`. argparse defines `--confidence` with
`choices=["verified", "planned", "speculative"]` and no `nargs='?'`, so it requires exactly
one argument. When the next token (another flag) starts with `-`, argparse raises:
  "argument --confidence: expected one argument" (exit code 2)
This makes _assert_success fail with an AssertionError for every character, which crashes the
session-scoped `pipeline_result` fixture before the chapter loop begins. All 12 test methods
will report "ERROR at setup of ..." rather than giving any useful signal.

The Neo-Tokyo location creation (line ~292) correctly passes `"planned"` after `--confidence`,
confirming this is an omission not a design intent. Verified with argparse reproduction:
  python3 -c "import argparse; p = argparse.ArgumentParser();
              p.add_argument('--confidence', choices=['verified','planned','speculative']);
              p.parse_args(['--confidence', '--first-appearance'])"
  → error: argument --confidence: expected one argument

Suggestion: Add "planned" after "--confidence" in the character creation block:

  "--confidence",
  "planned",       # <-- add this line
  "--first-appearance",
  "1",
```

---

### Warning Findings

```
[W-01] MAX_CONTEXT_TOKENS = 65536 defined but never used
Category: Testing
Severity: Warning
File: tests/integration/test_e2e_opencode.py
Lines: 38
Description: The constant is defined at module level but is not referenced anywhere in the
file. The name implies enforcement of a context window budget, but no such enforcement exists.
If intended as documentation of the model's context window, a comment should clarify. If it
was meant to cap scene generation context (e.g., passed as --max-tokens or used to truncate
story_elements), the enforcement is missing.
Suggestion: Either use the constant to limit context inputs passed to tool calls, or remove
it and add a docstring comment explaining the expected model context size.
```

```
[W-02] ANALYSIS_CHUNK_TYPES defined but never used — weakens test assertion
Category: Testing
Severity: Warning
File: tests/integration/test_e2e_opencode.py
Lines: 40-49, 748
Description: The constant enumerates all 8 expected analysis chunk types produced by
`outline_generator analyze-prompt`. The test asserts `len(chunk_files) >= 4` — half the
expected count. The constant exists but is not used to strengthen this assertion. As a result,
the test would pass even if only 4 of 8 chunks were generated (e.g., due to a partial LLM
failure during analysis), which undermines the intent of the test.
Suggestion: Use the constant to assert all expected chunks are present:

  for chunk_type in ANALYSIS_CHUNK_TYPES:
      expected_chunk = analysis_dir / f"{chunk_type}_chunk.md"
      assert expected_chunk.exists(), f"missing analysis chunk: {chunk_type}"

  # (or keep len assertion but use len(ANALYSIS_CHUNK_TYPES) as the threshold)
  assert len(chunk_files) >= len(ANALYSIS_CHUNK_TYPES)
```

```
[W-03] WIKI_READ_SCRIPT defined but never used — wiki-read has no integration coverage
Category: Testing
Severity: Warning
File: tests/integration/test_e2e_opencode.py
Lines: 72
Description: WIKI_READ_SCRIPT is defined pointing to src/tools/wiki_read.py but is never
referenced. This means the wiki-read/query path through the semantic search + context
assembly pipeline has no integration test coverage at all. The wiki snapshot path (via
WIKI_SNAPSHOT_SCRIPT) is tested, but read queries (the primary consumer of the wiki during
scene generation) are not exercised.
Suggestion: Either remove the constant and add a test assertion that exercises wiki_read
(e.g., verify that querying for "Alex" returns the character page), or document explicitly
that wiki-read coverage is deferred to a follow-up issue.
```

```
[W-04] No retry on generate_text transient failures — session-scoped fixture all-or-nothing
Category: Testing
Severity: Warning
File: tests/integration/test_e2e_opencode.py
Lines: 213-235 (character generation), 246-267 (setting generation)
Description: generate_text is called directly (synchronously, no retry) for character and
setting content generation. A single transient HTTP error, gateway timeout, or 503 from the
LLM endpoint raises RuntimeError, crashing the session-scoped fixture. Since the fixture is
session-scoped, this forces a full pipeline re-run from scratch to attempt recovery — even
if only one character generation step timed out.

The tool subprocess calls use their own _run_tool timeout but also have no retry. For a
long-running E2E suite (30–90 minutes per the docs), flakiness here is a real operational
risk in CI.

Suggestion: Wrap the direct generate_text calls and any calls where retry is safe (idempotent
steps with savepoint guards) with simple retry logic:

  from tenacity import retry, stop_after_attempt, wait_exponential

  @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=30))
  def _generate_with_retry(prompt: str) -> str:
      return generate_text(prompt)

  char_content = _generate_with_retry(char_prompt)

Note: _run_tool steps that call tools with internal savepoint guards are already
naturally retry-safe (the tool skips LLM inference if a savepoint exists).
```

```
[W-05] requests imported inside fixture body — violates import ordering convention
Category: Style
Severity: Warning
File: tests/integration/conftest.py
Lines: 14
Description: `import requests` appears inside the `llm_available` fixture function body,
not at module level. The project convention (copilot-instructions.md) requires imports at
module level, ordered stdlib → third-party → local. requests is a required dependency
(in requirements.txt) so deferred importing provides no benefit and creates inconsistency.
Suggestion: Move to module level:

  import requests  # at top of conftest.py, after stdlib imports
```

```
[W-06] Duplicate integration marker registration
Category: Style
Severity: Warning
File: tests/integration/conftest.py, pyproject.toml
Lines: conftest.py:8-10, pyproject.toml:10-12
Description: The `integration` marker is registered in two places: `pytest_configure` in
conftest.py (via `config.addinivalue_line`) and in `[tool.pytest.ini_options] markers` in
pyproject.toml. Both are valid mechanisms but serving the same purpose. Having both is
redundant and can cause confusion about which is authoritative.
Suggestion: Remove the `pytest_configure` hook from conftest.py and rely solely on the
pyproject.toml `markers` declaration. pyproject.toml is the canonical configuration source
for this project.
```

---

### Suggestions

```
[S-01] Missing trailing newline in docs/testing/integration-tests.md
Category: Documentation
Severity: Suggestion
File: docs/testing/integration-tests.md
Lines: 124 (EOF)
Description: The file ends with `r.md)` without a trailing newline character. POSIX convention
requires text files to end with a newline. This makes diff output slightly noisier and can
cause issues with some tooling.
Suggestion: Add a single newline at the end of the file.
```

```
[S-02] Wiki lint warnings printed to stdout but not captured in test output
Category: Testing
Severity: Suggestion
File: tests/integration/test_e2e_opencode.py
Lines: 794-797
Description: Lint warnings are printed with `print()` but only appear when running pytest
with -s (no capture). Without -s (the default CI mode), the warnings are swallowed and
provide no post-run diagnostic value. The test passes even if the LLM generates many
wiki-lint warnings, since only errors are asserted.
Suggestion: Consider accumulating warnings in the pipeline_result dict and reporting them
via a dedicated assertion or pytest.warns, or at minimum use pytest's built-in:

  # At the end of test_wiki_lint_no_errors:
  assert not warnings, f"wiki-lint produced {len(warnings)} warnings: {warnings}"
  # (or threshold-based: assert len(warnings) <= ACCEPTABLE_WARNING_COUNT)
```

```
[S-03] Session-scoped fixture failure gives poor diagnostic signal
Category: Testing
Severity: Suggestion
File: tests/integration/test_e2e_opencode.py
Lines: 107-666 (pipeline_result fixture)
Description: This is a well-understood tradeoff for E2E tests: the session-scoped fixture
runs the full pipeline once, and if any step fails, all 12 tests report "ERROR at setup"
with the same traceback. The pipeline has ~40+ tool calls across setup, 3 chapters, and
teardown. When a mid-pipeline step fails, there is no state snapshot indicating how far the
pipeline progressed.
Suggestion: Consider adding a `results["last_step"]` string that is updated just before each
major operation (e.g., "wiki_init", "outline_analyze_prompt", "chapter_1_scene_1", etc.).
On fixture failure, this would appear in the error traceback, immediately identifying which
stage failed without requiring a full re-run with -s.

  results["last_step"] = "wiki_init"
  r = _run_tool(WIKI_INIT_SCRIPT, ...)
  _assert_success(r, "wiki-init init")
  results["last_step"] = "outline_analyze_prompt"
  ...
```

---

## Agent File Changes (Carry-over)

The 25 agent file changes (24 `.agent.md` files + `_shared/dispatch-retry.md`) are all narrow model field migrations from OpenRouter-hosted models to Copilot-native models.

**Verification:**
- All `model:` fields are scalar strings (not arrays) — confirmed ✓
- All three reviewer variants (`reviewer-claude/gemini/gpt`) have identical body text, differing only in `name:`, `description:`, and `model:` — confirmed ✓
- Auditor variants in sync — confirmed ✓
- Researcher variants in sync — confirmed ✓
- `test-writer.agent.md` has one additional substantive change: a new prohibition against `sys.modules` module-level mocking. This is a valid and useful guard drawn from prior test suite pollution incidents — confirmed correct ✓
- `dispatch-retry.md` adds guidance for agents that return "no changes made" responses, distinguishing trivial from non-trivial escalation paths — confirmed correct ✓

No numbered step gaps detected in orchestrator or other agent files reviewed.

---

## Overall Assessment

The integration test suite represents a significant quality milestone — a full-pipeline E2E test was previously absent. The architecture (session-scoped fixture running the pipeline once, 12 assertion methods against pre-computed results) is appropriate for this use case and the test coverage across story state, wiki, outline, scenes, savepoints, recaps, and linting is comprehensive.

**The PR is not ready to merge as-is.** The missing `"planned"` value after `--confidence` in the character wiki creation loop (C-01) is a one-line fix, but it will cause a complete fixture failure before any chapter generates — meaning the test suite provides no value in its current state. All other findings are correctness improvements or code hygiene issues that do not block merge, but W-02 (weak chunk count assertion) and W-03 (wiki-read has no integration coverage) represent meaningful gaps in test confidence that should be tracked.

Recommended actions before merge:
1. **Fix C-01** (add `"planned"` after `"--confidence"` in the character creation block)
2. Consider **W-02** (strengthen chunk file assertion using ANALYSIS_CHUNK_TYPES)
3. File a follow-up issue for **W-03** (wiki-read integration coverage)
4. Address **W-04–W-06** in a follow-up or in this PR if low effort
