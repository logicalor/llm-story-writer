## Synthesized Code Review — 2026-04-14 — PR #54

**Review Type:** Multi-model synthesis (Claude Opus 4.6 + GPT 5.4 + Gemini 3.1 Pro)
**Branch:** feat/issue-15-wiki-snapshot
**PR:** #54
**Issue:** #15
**Model Agreement Score:** 8/10
**Overall Assessment:** Needs Fixes

---

### Synthesis Overview

This PR implements the wiki-snapshot tool — a three-stage hybrid retrieval pipeline (ADR 005) for assembling pre-generation scene context from wiki pages. All three models agreed the implementation is well-structured, follows project conventions (ADR 001 hybrid pattern, clean architecture), and includes comprehensive test coverage (15 tests). Agreement was very high: all three independently identified the delta cache disconnect and the O(n²) budget enforcement, and all three noted the silent exception handling. The primary divergence was severity classification of the cache finding (2 Critical vs 1 Warning). One significant finding — RRF scores computed but never used — was uniquely identified by GPT and verified as genuine dead code.

**Model Agreement Score:** 8/10 — strong convergence on core issues with minor divergences on severity and a few unique observations per model.

### Individual Report Summaries

| Model  | Overall Assessment                    | Unique Focus Areas                                          | Critical Count | Warning Count |
| ------ | ------------------------------------- | ----------------------------------------------------------- | -------------- | ------------- |
| Claude | Fix C-01 then merge                  | Entity types silently dropped, Characters heading unconditional, TypeScript error format | 1              | 4             |
| GPT    | Address W-01+W-02 before merge       | RRF dead code (unique), test file formatting, null bytes, doc stats mismatch, argparse exit codes | 0              | 3             |
| Gemini | Fix C-01 then merge                  | Wikilink slug validation (unique), TypeScript Zod validation, scene parameter annotation | 1              | 3             |

---

### Consensus Findings

#### ★★★ Unanimous Findings (All Three Models Agree)

```
[U-C-01] Delta cache rendered content is computed but never used by assembly
Severity: Critical
Category: Correctness
File: src/tools/wiki_snapshot.py
Lines: 1034-1048 (cache building), 607-750 (_assemble_context)
Detail: In cmd_snapshot(), `rendered_content` is populated at lines 1034-1040
  using cached content for cache hits and fresh rendering for misses. However,
  `_assemble_context()` (called at line 1043) does NOT accept or use
  `rendered_content` — it independently calls `_get_page_content_at_level()`
  for every page, re-rendering everything from scratch regardless of cached
  content.

  Consequences:
  1. Cache hits are counted in stats but cached content is discarded — the
     optimization is illusory.
  2. The `rendered_content` dict is saved to the cache file for future
     invocations, but on those invocations the same pattern repeats.
  3. If a cached page's detail level changes between runs (e.g., demoted by
     budget enforcement), stale cached content would be stored alongside the
     new level, creating a potential inconsistency.
  4. Tests pass because they verify stats (cache_hits > 0) but do not verify
     that cached content strings appear in the output.
Models: Claude ✓ GPT ✓ Gemini ✓
Suggestion: Modify `_assemble_context()` to accept an optional
  `rendered_content: dict[str, str]` parameter and use it as a lookup before
  calling `_get_page_content_at_level()`. When `rendered_content[slug]` exists,
  use it; otherwise fall back to `_get_page_content_at_level()`.
```

```
[U-W-01] O(n²) token recalculation in _enforce_token_budget
Severity: Warning
Category: Performance
File: src/tools/wiki_snapshot.py
Lines: 565-602
Detail: `_enforce_token_budget` calls `_total_tokens()` inside a while loop.
  Each call iterates ALL pages, calling `_get_page_content_at_level()` +
  `count_tokens()` for each. Each demotion of a single page triggers a full
  re-scan: O(N pages) × O(M demotions) = O(N×M) total work. For typical wiki
  sizes (50-200 pages) the word-based token counter is fast enough, but this
  scales poorly and would become a bottleneck with a proper tokenizer.
Models: Claude ✓ GPT ✓ Gemini ✓
Suggestion: Maintain a running total and per-slug token cache. After each
  demotion, subtract the old page token count and add the new count:
    total = _total_tokens()
    while total > budget:
        old = count_tokens(_get_page_content_at_level(page, old_level))
        new = count_tokens(_get_page_content_at_level(page, new_level))
        total -= old; total += new
```

```
[U-W-02] Bare except Exception with silent pass in Tier 2 and Tier 3
Severity: Warning
Category: Correctness
File: src/tools/wiki_snapshot.py
Lines: 197, 218, 242
Detail: Three `except Exception: pass` blocks in `_tier2_metadata_query()` and
  `_tier3_semantic_search()` silently swallow all exceptions from ChromaDB
  operations. While graceful degradation when ChromaDB is unavailable is the
  correct design intent (matching ADR 005), completely silent failure masks
  programming errors (KeyError, TypeError, AttributeError) and genuine
  infrastructure problems (corrupt indices, permission errors). For a
  retrieval pipeline where T2/T3 are core tiers, silently losing all metadata
  and semantic results could produce significantly degraded snapshots without
  any diagnostic signal.
Models: Claude ✓ GPT ✓ Gemini ✓
Suggestion: Log caught exceptions to stderr for diagnostic visibility:
    except Exception as exc:
        sys.stderr.write(f"Warning: T2 metadata query failed: {exc}\n")
```

#### ★★☆ Majority Findings (Two of Three Models Agree)

```
[M-S-01] Unused parameters in _assemble_context signature
Severity: Suggestion
Category: Style
File: src/tools/wiki_snapshot.py
Lines: 607-615
Detail: The `outline` and `scene_type` parameters are accepted by
  `_assemble_context()` but never referenced in the function body. Note:
  `scene_type` IS used by `_assign_detail_levels()` (a different function,
  lines 526/530), so it's only unused specifically within `_assemble_context`.
  These dead parameters add confusion — callers pass them but they have no
  effect on assembly output.
Models: Claude ✓ GPT ✗ Gemini ✓ (Gemini noted only `outline`)
Dissenting view: GPT did not report this finding.
Suggestion: Remove unused parameters from the signature and call site, or
  use them (e.g., include outline text in the assembled context). If reserved
  for a future feature, add them when implemented.
```

```
[M-S-02] Early validation of scene+outline for snapshot operation
Severity: Suggestion
Category: Correctness
File: src/tools/wiki_snapshot.py (lines 891-894), .opencode/tools/wiki-snapshot.ts (lines 19-24)
Detail: The `--scene` and `--outline` parameters are optional at the argparse
  level but required for the snapshot operation. Validation is done manually
  in `cmd_snapshot()`, producing exit-code-1 rather than argparse's exit-code-2
  for argument errors. GPT noted the Python-side argparse concern; Gemini noted
  the TypeScript-side Zod schema could add a `.refine()` to fail before
  subprocess invocation.
Models: Claude ✗ GPT ✓ Gemini ✓
Dissenting view: Claude did not report this finding.
Suggestion: Either use argparse subparsers to declare scene/outline as
  required for the snapshot operation, or add a Zod `.refine()` in the
  TypeScript wrapper to validate before invoking Python.
```

#### ★☆☆ Singular Findings (Only One Model Reported)

```
[S-W-01] RRF scores computed but never used in relevance scoring
Severity: Warning
Category: Correctness
File: src/tools/wiki_snapshot.py
Lines: 350-356
Detail: The `rrf_scores` dict is computed via Reciprocal Rank Fusion at
  lines 350-356 but is never referenced after that point. The final relevance
  score (lines 432-440) uses entity_match, wikilink_proximity,
  semantic_similarity, recency, and type_priority — but NOT the RRF score.
  ADR 005 and docs/tools.md both document "merged via Reciprocal Rank Fusion"
  as a key design element, but RRF is effectively dead code. The current
  weighted-sum formula works correctly, but the implementation does not match
  the documented architecture.
Model: GPT
Assessment: VERIFIED — grep confirms `rrf_scores` appears only at lines 352
  and 356 (computation). No usage after line 356. This is genuine dead code
  and a design-implementation divergence. The function's docstring says "Merge
  all tiers via RRF" but RRF is computed and discarded. This is a significant
  correctness finding that the other two models missed.
```

```
[S-W-02] Wikilink-extracted slugs bypass _validate_slug
Severity: Warning (downgraded from Gemini's original: mitigated by defense-in-depth)
Category: Security
File: src/tools/wiki_snapshot.py
Lines: 282-293
Detail: In `_tier4_wikilink_traversal`, wikilink targets extracted via
  `re.findall(r"\[\[([^\]]+)\]\]", body)` are used directly as slugs passed
  to `_find_page_by_slug()` without first calling `_validate_slug()`. A
  crafted wikilink like `[[../../etc/passwd]]` would bypass slug validation.
  The risk is mitigated by `_find_page_by_slug()` → `find_pages()` →
  `_filter_within_wiki()` which provides path traversal protection at a
  deeper layer.
Model: Gemini
Assessment: Genuine defense-in-depth gap, but not exploitable given the
  existing protection in `find_pages()`. Worth fixing for belt-and-suspenders
  safety: add `if ".." in slug or "/" in slug: continue` before the lookup.
```

```
[S-S-01] Entity types silently dropped from assembly output
Severity: Suggestion
Category: Correctness
File: src/tools/wiki_snapshot.py
Lines: 621-750
Detail: `_assemble_context()` only renders pages of types: character, location,
  plot_thread, world_rule, event, relationship. The wiki supports additional
  types (faction, item, theme, timeline_entry, chapter_synopsis) defined in
  `_wiki.py`'s `_TYPE_TO_DIR`. Pages of these types could be retrieved and
  scored by Stage 1/2/3 but would be silently omitted from the output.
Model: Claude
Assessment: Likely intentional — ADR 005 only specifies sections for the six
  listed types. But a catch-all "## Other Context" section or a debug log
  when pages are retrieved but not rendered would prevent silent data loss.
```

```
[S-S-02] Characters heading emitted unconditionally (empty section)
Severity: Suggestion
Category: Style
File: src/tools/wiki_snapshot.py
Lines: 623
Detail: The "## Characters" heading is appended unconditionally, even when
  no character pages are retrieved. All other section headings (Location,
  Plot Threads, etc.) are conditional on having matching pages.
Model: Claude
Assessment: Minor inconsistency. Easy fix: wrap in the same conditional
  pattern used by other sections.
```

```
[S-S-03] Test file not formatted per ruff
Severity: Suggestion
Category: Style
File: tests/unit/test_wiki_snapshot_tool.py
Lines: general
Detail: `ruff format --check` reports this file would be reformatted.
Model: GPT
Assessment: Should be fixed before merge — run `ruff format`.
```

```
[S-S-04] _validate_slug does not reject null bytes (pre-existing)
Severity: Suggestion
Category: Security
File: src/tools/_wiki.py
Lines: 172-179
Detail: `_validate_slug()` checks for `..` and `/` but not null bytes. Not
  exploitable (Python rejects null bytes in paths) but produces an unclean
  error. This is a pre-existing issue, not introduced by this PR.
Model: GPT
Assessment: Out of scope for this PR. File as a follow-up issue if desired.
```

```
[S-S-05] Documentation stats imply pages_retrieved ≠ pages_included but they're always equal
Severity: Suggestion
Category: Documentation
File: docs/tools.md
Lines: wiki-snapshot section (example JSON output)
Detail: The example JSON shows `"pages_retrieved": 12, "pages_included": 10`,
  implying these values can differ. In the implementation, both are set from
  `len(pages)` — `pages_retrieved` at line 1012, `pages_included` at line 1061
  — and no pages are removed between those lines.
Model: GPT
Assessment: Verified — both stats derive from the same dict after threshold
  filtering. Either make the example values equal or set `pages_retrieved`
  before threshold filtering to reflect the intended semantics.
```

```
[S-S-06] No test for empty wiki / missing wiki directory
Severity: Suggestion
Category: Testing
File: tests/unit/test_wiki_snapshot_tool.py
Lines: general
Detail: No test for a wiki directory with no `index.md`, or a story with no
  wiki directory at all (the "No wiki found" branch at line 901).
Model: Claude
Assessment: Minor gap — the branches exist in the code but are untested.
  Worth adding for completeness.
```

```
[S-S-07] Test count confirmation
Severity: Suggestion
Category: Documentation
File: tests/unit/test_wiki_snapshot_tool.py
Lines: 1-5
Detail: The PR description says "15 verification tests" but the test file has
  12 classes with varying method counts. The actual test method count should
  be confirmed via `pytest --collect-only -q`.
Model: Gemini
Assessment: Minor documentation accuracy concern.
```

---

### Divergence Analysis

```
[D-01] Topic: Severity of delta cache finding
Claude says: Critical — cache optimization is non-functional, must fix before merge
GPT says: Warning — implementation diverges from docs but doesn't cause incorrect output
Gemini says: Critical — illusory optimization, potential stale content inconsistency
Assessment: The 2-vs-1 split favors Critical. While the tool produces correct
  snapshot content without the cache, a feature that appears to cache but
  doesn't is misleading. It also wastes I/O writing cache files that are never
  read back effectively. The stale detail-level risk (Gemini's point) adds
  weight. Resolved as Critical.
```

```
[D-02] Topic: Severity of bare except clauses
Claude says: Warning — masks programming errors during development
GPT says: Suggestion — graceful degradation is correct design
Gemini says: Warning — silent failure in core tiers degrades snapshots
Assessment: The 2-vs-1 split favors Warning. GPT correctly notes the design
  intent is graceful degradation, but the implementation is too broad —
  catching all Exception types prevents debugging of real bugs. A Warning
  with a targeted fix (log + narrow exception type) is appropriate. Resolved
  as Warning.
```

```
[D-03] Topic: RRF scores — genuine dead code or false positive?
Claude says: (not reported)
GPT says: Warning — RRF computed at lines 350-356 but never used in scoring formula
Gemini says: (not reported)
Assessment: VERIFIED via grep. Only GPT identified this, but it is genuine
  dead code — `rrf_scores` is computed and immediately abandoned. The
  function's docstring says "Merge all tiers via RRF" and ADR 005 documents
  RRF as a key design element, but the actual scoring formula uses a
  weighted sum of five other signals. This is a significant
  design-implementation divergence. Elevated to the Recommended Actions
  despite being a singular finding because it was verified as genuine.
```

---

### Recommended Actions (Prioritized)

```
1. [U-C-01] ★★★ Fix: Connect delta cache to assembly — pass rendered_content
   to _assemble_context() and use cached strings instead of re-rendering
   (Critical — all models agree)

2. [S-W-01] ★☆☆ Fix: Either integrate rrf_scores into the relevance formula
   or remove the dead RRF computation and update ADR 005 + docs/tools.md
   (Warning — 1 model, but verified genuine dead code)

3. [U-W-01] ★★★ Fix: Optimize _enforce_token_budget with running total
   instead of O(n²) recalculation (Warning — all models agree)

4. [U-W-02] ★★★ Fix: Add stderr logging to bare except blocks and narrow
   exception types (Warning — all models agree)

5. [S-W-02] ★☆☆ Fix: Add slug validation for wikilink-extracted slugs in T4
   traversal — defense-in-depth (Warning — 1 model, mitigated)

6. [S-S-02] ★☆☆ Fix: Wrap "## Characters" heading in conditional check
   matching other sections (Suggestion — 1 model, trivial fix)

7. [S-S-03] ★☆☆ Fix: Run ruff format on test file (Suggestion — 1 model)

8. [S-S-05] ★☆☆ Fix: Align example JSON stats or adjust pages_retrieved
   semantics (Suggestion — 1 model)

9. [M-S-01] ★★☆ Consider: Remove unused outline/scene_type params from
   _assemble_context (Suggestion — 2 models)

10. [M-S-02] ★★☆ Consider: Early validation of scene+outline at argparse
    or Zod level (Suggestion — 2 models)

11. [S-S-01] ★☆☆ Consider: Add catch-all section for unhandled entity types
    (Suggestion — 1 model)

12. [S-S-06] ★☆☆ Consider: Add tests for empty wiki / missing wiki directory
    (Suggestion — 1 model)
```
