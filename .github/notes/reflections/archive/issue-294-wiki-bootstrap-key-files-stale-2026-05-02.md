---
date: "2026-05-02"
issue: 294
pr: 306
category: instruction
targets:
  - "docs/features/wiki-maintainer.md"
severity: minor
---

## `wiki-maintainer.md` Key Files table omits `bootstrap_wiki_from_story()` entry point

### Finding

After PR #306 added `bootstrap_wiki_from_story()` as a public programmatic API in
`src/tools/wiki_extract.py` (exported in `__all__`), the Key Files table in
`docs/features/wiki-maintainer.md` still described that file as:

> Extraction pipeline and programmatic `update_wiki_from_chapter()` API used after each chapter

The description makes no mention of the new bootstrap entry point, giving readers the
impression that the file only handles post-chapter incremental updates. Additionally,
`tests/unit/test_wiki_bootstrap.py` (5 tests covering the new bootstrap function) is
absent from the Key Files table, whereas the companion `tests/unit/test_wiki_maintainer.py`
is listed.

### Observation

When a file gains a second public entry point, the Key Files table description becomes
misleading rather than merely incomplete — it actively directs readers toward only one
mode of use. The pattern "stale-description-after-adding-API" has recurred previously
(issue #293: `outline` computed variable described as reserved after it was populated).
Feature docs should be updated as part of the same PR that adds the API.

### Suggested Improvement

1. Update the `src/tools/wiki_extract.py` row in the Key Files table to mention both
   programmatic entry points.
2. Add a `tests/unit/test_wiki_bootstrap.py` row to the Key Files table.

### Action Taken

Applied:
- Updated `src/tools/wiki_extract.py` description in Key Files table to mention both
  `bootstrap_wiki_from_story()` and `update_wiki_from_chapter()`.
- Added `tests/unit/test_wiki_bootstrap.py` row to Key Files table.
