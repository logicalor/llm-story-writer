---
date: "2026-04-14"
issue: 9
pr: 44
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## Sixth tool implementation confirms maturity — shared LLM module, pattern carry-forward, false-positive handling

### Finding

Issue #9 (Build recap-manager Tool) was the sixth tool implementation and the first requiring LLM access. Three positive signals:

1. **Shared module pattern applied proactively.** The Coder created `src/tools/_llm.py` as a shared LLM client rather than embedding API calls directly in `recap_manager.py`. This follows the extraction precedent from `_io.py` (issue #40). The `_`-prefixed private module convention in `src/tools/` is now an established pattern for shared utilities.

2. **All established patterns applied on first pass.** Path validation (`is_relative_to`), error handling to stderr, JSON output format, `sys.path` idempotent guards — all correct without review-fix cycles. Continues the positive trend from issue #11.

3. **GPT false-positive handled correctly.** GPT raised a Critical finding about `_filter_aged_events` (now `_filter_low_importance_events`) behaviour, claiming it didn't match legacy code. Verified against `legacy/src/` — behaviour was correct. Downgraded to Suggestion, renamed for clarity. The Synthesized Review consensus mechanism worked: Gemini and Claude didn't flag it, GPT's outlier finding was investigated rather than blindly applied.

4. **Review finding quality.** Four actionable warnings (dead code, sys.path guards, monkeypatch cleanup, misleading name) and one suggestion (missing helper tests). All were genuine improvements. Zero false negatives on code quality.

### Observation

The tool implementation pipeline is maturing. Six tools in, the Coder is consistently applying all codified patterns. The shared module convention (`_io.py`, `_llm.py`) demonstrates the value of the pending Rule 10 proposal (prior-tool review) — the Coder is already doing this informally. The `sys.path` idempotent guard (U-W-02) is a new pattern worth codifying: `if path not in sys.path: sys.path.insert(0, path)`.

Notable: recap-manager had no atomic writes (read-only operations use savepoint repository directly), so `_io.py` was correctly not imported. Pattern application includes knowing when NOT to apply a pattern.

When `patterns.md` and the `conventions` collection are created (pending issue #7 proposal), include:
- Shared utility convention: `src/tools/_*.py` for shared modules
- `sys.path` idempotent guard pattern
- LLM access via `_llm.py` (generate_text, generate_json, _extract_json_block)

### Suggested Improvement

No agent/skill/instruction changes needed. Positive signals recorded for future pattern documentation.

### Action Taken

No action needed — positive signal recorded. Reinforces pending issue #7 proposal (conventions collection).
