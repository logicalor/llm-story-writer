# Code Review Report — fix/issue-89-strengthen-chunk-count-assertion

**Date:** 2026-04-17
**Branch:** `fix/issue-89-strengthen-chunk-count-assertion`
**Commit:** `964bb41 fix(tests): strengthen chunk assertion + remove unused constant (#89)`
**Reviewer:** Claude (Sonnet 4.6)

---

## Review Summary

This is a focused, two-part test quality fix: removal of an unused module-level constant (`MAX_CONTEXT_TOKENS`) that was previously flagged in review, and strengthening of a chunk-existence assertion from a loose numeric lower bound (`>= 4`) to an explicit per-type file existence check covering all eight expected chunk types. Both changes are correct, the chunk type list matches the production constant exactly, and the deleted constant has no other references in the codebase. No correctness, security, or performance issues were found.

**Files Reviewed:** 1
**Findings:** 0 Critical, 0 Warning, 1 Suggestion

---

## Findings

### Critical Findings

None.

### Warning Findings

None.

### Suggestions

```
[S-01] ANALYSIS_CHUNK_TYPES duplicates the production CHUNK_TYPES constant
Category: Testing
Severity: Suggestion
File: tests/integration/test_e2e_opencode.py
Lines: 41-49
Description: ANALYSIS_CHUNK_TYPES in the test file is byte-for-byte identical to
CHUNK_TYPES defined in src/tools/outline_generator.py (verified via grep). If the
production code adds, removes, or renames a chunk type, the test constant must be
updated in a separate edit, creating an implicit maintenance coupling with no
compile-time enforcement. The previous review (2025-07-14-pr87-claude-raw.md)
flagged the unused MAX_CONTEXT_TOKENS constant; this PR correctly removes it, but
the same class of silent duplication remains with ANALYSIS_CHUNK_TYPES.
Suggestion: Import the production constant directly to keep a single source of truth:

    from src.tools.outline_generator import CHUNK_TYPES as ANALYSIS_CHUNK_TYPES

This eliminates the duplication without changing any test logic.
```

---

## Phase Notes

### Phase 1 — Structural

- **Commit message:** Follows convention (`fix(tests):`), references issue number (#89). ✓
- **Branch name:** Follows convention (`fix/issue-N-description`). ✓
- **Scope:** Minimal — 6 lines changed across a single file. ✓
- **No unrelated changes:** Both modifications (constant removal, assertion replacement) are directly related to the stated purpose. ✓
- **Numbered step lists, file relocation, tools array coupling, model variant sync, shell snippet safety:** Not applicable — no agent, skill, or workflow files were modified.

### Phase 2 — Code Review

The replacement comment for `MAX_CONTEXT_TOKENS` is accurate and actionable: it explains that the LLM service naturally caps inputs, so no explicit truncation constant is needed in the test. The constant has no references anywhere in the live codebase (confirmed by grep; the sole match is a prior review report noting it was unused).

The new assertion loop is idiomatic and correct. It iterates `ANALYSIS_CHUNK_TYPES`, constructs the expected path under `story_dir / "savepoints" / "story_analysis"`, and asserts `exists()` with an informative failure message. This matches the savepoint path convention used in the production tool (`step = f"story_analysis/{chunk_type}_chunk"`, stored as `.md` by `FilesystemSavepointRepository`), which was confirmed by inspecting `src/tools/outline_generator.py`.

The `ANALYSIS_CHUNK_TYPES` tuple matches `CHUNK_TYPES` in `src/tools/outline_generator.py` exactly — same eight values, same order.

### Phase 3 — Frontend

Not applicable.

### Phase 4 — Security

Not applicable. Test file only; no user input, no credentials, no external calls introduced.

### Phase 5 — Testing

The strengthened assertion is a genuine quality improvement:

- The old `assert len(chunk_files) >= 4` would pass silently if only four of eight expected chunks were present, masking a partial pipeline failure.
- The new assertion tests for every specific chunk type and surfaces exactly which chunk is missing on failure, making CI output actionable.
- The chunk type list is verified to match the production `CHUNK_TYPES` constant, so the assertion tests the actual contract.

The one testing concern is the duplication risk described in S-01 above.

### Phase 6 — Performance

Not applicable.

### Phase 7 — Documentation

No documentation changes were required or made. The explanatory comment replacing `MAX_CONTEXT_TOKENS` is clear and correct. No existing docs reference `MAX_CONTEXT_TOKENS`.

---

## Overall Assessment

The PR is ready to merge. Both changes are correct and improve test quality without introducing regressions. The assertion now tests the full contract (all eight chunk types present by name) instead of a weak lower bound, and the removal of the unused constant addresses a previously reported review finding. The one suggestion (importing `CHUNK_TYPES` from production rather than duplicating it) is a low-priority maintenance hygiene improvement that can be deferred to a follow-up if desired.
