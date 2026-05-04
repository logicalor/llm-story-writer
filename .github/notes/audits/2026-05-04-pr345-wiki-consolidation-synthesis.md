## Synthesized Audit — 2026-05-04 (PR #345)

**Audit Type:** Multi-model synthesis (Claude Sonnet 4.6 · GPT · Gemini)
**Audit Scope:** PR #345 / Issue #344 — wiki consolidation implementation verification
**Model Agreement Score:** 6/10
**Overall Health:** Mostly Fixed — structural consolidation complete; one critical persistence bug and several test coverage gaps remain
**Development Stage:** Phase 7 complete structurally; Phase 7d has a critical persistence guard bug

### Prior Audit Resolutions

All five issues from 2026-05-04-wiki-consolidation-synthesis.md are structurally resolved:

| Prior Finding | Status |
| ------------- | ------ |
| [U-C-01] Bootstrap entity coverage gap | ✅ RESOLVED — sheets are now primary source |
| [U-C-02] Recap events not in wiki/ChromaDB | ✅ RESOLVED — `_sync_recap_events_to_wiki()` wired |
| [M-C-01] Parallel sheet evolver mutation | ✅ RESOLVED — evolvers removed from chapter loop |
| [M-W-01] Dual injection (wiki + raw sheets) | ✅ RESOLVED — sheets cleared when wiki succeeds |
| [M-W-02] ADR 004 not completed | ✅ RESOLVED — ADR marked Accepted |

### Finding Counts by Consensus

| Consensus         | Critical | Warning | Info |
| ----------------- | -------- | ------- | ---- |
| ★★★ Unanimous     | 0        | 1       | 5    |
| ★★☆ Majority      | 0        | 3       | 0    |
| ★☆☆ Singular      | 1 (CRITICAL) | 1   | 2    |

### Key Findings

- [U-R-01–04] All five prior critical issues resolved (★★★) — structural consolidation complete
- [U-W-01] Direct-path prompts render empty entity section blocks — token waste (★★★)
- [S-C-01] **CRITICAL** — Recap compact/sanitised persistence gated inside `if recap_result.get("events"):` guard — eventless chapters lose narrative continuity context (★☆☆ singular, Claude only — but analysis is compelling)
- [M-W-01] Non-sheet entity types (faction, item, plot_thread) still outline-only for bootstrap (★★☆)
- [M-W-02] Scene snapshot override chain not verified in test suite (★★☆)
- [M-W-03] No end-to-end test: recap event write → ChromaDB → retrieval (★★☆)
- [S-W-01] ADR 004 body describes per-scene wiki updates that don't exist (★☆☆)
- [S-I-01] Pre-drafting prompts (synopsis, expand_to_scenes) correctly wired — positive confirmation (★☆☆)
- [S-I-02] Stale legacy `sheet-evolution` vocabulary in test fixtures (★☆☆)

### Divergences

- [D-01] **Recap persistence guard**: Claude says CRITICAL — entire state.recaps update gated on events existence; GPT says acceptable; Gemini says safety feature. Claude is most likely correct — compact/sanitised are prose summaries, not event data. Gating them on LLM-enumerated event presence is semantically incorrect. See `src/presentation/orchestrator.py` ~line 1828.
- [D-02] Non-sheet entity coverage: Claude + GPT flag Warning; Gemini silent. Claude/GPT correct.
- [D-03] ADR 004 body accuracy: GPT flags Warning; others silent. GPT correct.

### Recommended Priority Actions

1. Fix `src/presentation/orchestrator.py` ~line 1828 — move `state.recaps[str(chapter_number)]` write outside the `if recap_result.get("events"):` guard; only `_sync_recap_events_to_wiki()` should be conditional
2. Add end-to-end test: recap event write → ChromaDB upsert → get_snapshot() retrieval
3. Add test asserting scene-level snapshot content appears in rendered prompt payload
4. Document non-sheet entity type bootstrap limitation in ADR 004 or feature docs
5. Correct ADR 004 body — per-scene wiki updates are not implemented
6. Clean up stale `sheet-evolution` test fixture keys

### Actions Taken

- Notes written: `.github/notes/audits/2026-05-04-pr345-wiki-consolidation-synthesis.md`
- ChromaDB: key findings embedded into `audits` collection
- Issues created: pending user approval
