# Plan — Issue #212: Strengthen live headless E2E artifact assertions after wiki initialization

## Summary
Extend the existing live headless E2E in `tests/integration/test_end_to_end_headless.py` to assert that the completed pipeline produces wiki artifacts. Wiki initialization was already wired in PR #216 (commit b203a19). This change adds focused assertions only — no production code changes.

## Affected Areas
- Testing: `tests/integration/test_end_to_end_headless.py`
- No production code changes
- No ChromaDB schema changes

## Task Checklist

1. Add wiki directory existence assertion (`wiki/`)
2. Add `wiki/index.md` existence assertion
3. Add `wiki/log.md` existence + content assertion (must contain `[batch]` entries)
4. Add `pipeline_state.json` `wiki_batches` assertion:
   - Key exists
   - Is a list with >= 2 entries (one per chapter)
   - Each entry has `story_name`, `chapter_number`, `updated_pages`, `new_pages`
   - `updated_pages` and `new_pages` are lists
5. Add wiki subdirectory existence assertion (at least `timeline/`)
6. Add `wiki/_schema.md` and `wiki/contradictions.md` existence assertions

## Execution Order
Implementation → Verification tests → Confirm all pass

## Risks & Edge Cases
- Wiki pages are LLM-extracted; counts of new/updated pages may be zero. Do NOT assert non-empty `new_pages` or `updated_pages`.
- `log.md` content depends on `run_batch` logging, which is deterministic.
- E2E is gated behind `@pytest.mark.integration` and auto-skips if LM Studio is unavailable.

## PR Description Template

### Summary
Strengthens live headless E2E assertions for wiki artifacts after wiki initialization fix.

### Closes
Closes #212

### Changes
- [x] E2E asserts wiki directory initialization
- [x] E2E asserts wiki log and index files
- [x] E2E asserts `wiki_batches` persisted in pipeline state
- [x] All tests passing (verified)
- [x] Linting clean
