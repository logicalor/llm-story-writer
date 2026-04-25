## Synthesized Audit — 2026-04-25

**Audit Type:** Multi-model synthesis (Claude Opus 4.6 + GPT 5.4 + Gemini 3.1 Pro)
**Model Agreement Score:** 9/10
**Overall Health:** At Risk
**Development Stage:** Python-native migration — structural skeleton complete; generation capability incomplete

### Finding Counts by Consensus

| Consensus         | Critical | Warning | Info |
| ----------------- | -------- | ------- | ---- |
| ★★★ Unanimous     | 5        | 4       | 0    |
| ★★☆ Majority      | 1        | 7       | 1    |
| ★☆☆ Singular      | 1        | 1       | 2    |

### Key Findings

- [U-C-01] Assembly phase is a no-op stub — pipeline produces no story file on disk (★★★)
- [U-C-02] Characters and Settings phases are stubs — no context injected into chapters (★★★)
- [U-C-03] Final-edit phase is a stub — prose never quality-reviewed (★★★)
- [U-C-04] WikiMaintainerAgent discards all LLM output — wiki never updated (★★★)
- [U-C-05] ConsistencyCheckerAgent always returns "passed" — output discarded (★★★)
- [U-W-06] TUI does not support resume_pipeline (★★★)
- [U-W-07] CLI --batch flag silently ignored (★★★)
- [U-W-08] E2E test validates pipeline_state.json only, not real story output (★★★)
- [U-W-09] Legacy test_e2e_opencode.py retained after OpenCode removed (★★★)
- [M-C-10] Validation baseline red — lint/mypy/19 unit test failures (★★☆)
- [M-W-11] Narrative-arc phase absent from orchestrator (★★☆)
- [M-W-12] Application services layer orphaned — not called by new orchestrator (★★☆)
- [M-W-13] TUI Ctrl+S and Ctrl+C overpromise their behaviour (★★☆)
- [M-W-14] Resume semantics shallow — always loads latest snapshot (★★☆)
- [M-W-15] Docs/ADR lag — ADR 007 status "Proposed", README overstates wiki capability (★★☆)
- [M-W-16] Textual version hint in CLI error message stale (0.85.x vs 6.x) (★★☆)
- [S-C-18] aiohttp missing from pyproject.toml — may block test collection in clean venv (★☆☆)
- [S-W-21] pytest testpaths limits default collection to tests/unit only (★☆☆)
- [S-I-19] story_orchestrator.py is dead code (★☆☆)
- [S-I-20] print() used for logging in openai_async_provider.py (★☆☆)

### Divergences

- [D-01] aiohttp — Gemini found it blocking; Claude/GPT had tests running. Resolution: likely transitive dep in test environment; add explicitly to pyproject.toml as precaution.
- [D-02] requests dependency — Gemini said remove; Claude+GPT confirmed it's live in _llm.py. Resolution: keep until sync provider retired.

### Actions Taken

- Notes written: `.github/notes/audits/2026-04-25-synthesis.md`
- ChromaDB: findings embedded in `audits` collection
