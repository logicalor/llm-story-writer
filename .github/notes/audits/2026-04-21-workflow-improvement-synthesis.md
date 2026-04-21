## Synthesized Audit — 2026-04-21

**Audit Type:** Multi-model synthesis (Claude Opus 4.6 + GPT 5.4 + Gemini 3.1 Pro)
**Focus:** Workflow improvement — savepoints/memory, token efficiency, structural clarity, logic gaps
**Model Agreement Score:** 7/10
**Overall Health:** At Risk — one unanimous critical defect (empty character/setting sheets) poisons entire downstream pipeline
**Development Stage:** Phase 8 (per-chapter loop) — functionally blocked by empty sheet generation and unimplementable quality gate

### Finding Counts by Consensus

| Consensus         | Critical | Warning | Info |
| ----------------- | -------- | ------- | ---- |
| ★★★ Unanimous     | 1        | 0       | 0    |
| ★★☆ Majority      | 2        | 3       | 0    |
| ★☆☆ Singular      | 2        | 8       | 5    |

### Key Findings

- [U-C-01] Phase 5/6 write empty character/setting sheets — no LLM generation step (★★★)
- [M-C-01] Phase 8f chapter quality gate not implementable — critique-runner is outline-only (★★☆)
- [M-C-02] Phase 8c invocation model contradictory — orchestrator says post-chapter, wiki-maintainer says post-scene (★★☆)
- [M-W-01] Chunked outline previousChunks accumulation causes quadratic token growth (★★☆)
- [M-W-02] Resume logic: no mechanism to determine current pipeline phase (★★☆)
- [M-W-03] Phase 9 assembly underspecified — no tools, no format, no output path (★★☆)
- [S-C-01] Wiki-snapshot token enforcement never drops pages — budget can overflow (★☆☆)
- [S-C-02] Context window mismatch: pipeline assumes 65k, active config is 16384 (★☆☆)
- [S-C-03] Critique-runner savepoint namespace collision between outline and chapter quality loops (★☆☆)
- [S-W-01] Analysis chunk savepoint paths: code vs docs mismatch (★☆☆)
- [S-W-02] Non-chunked outline savepoint name mismatch: initial_outline vs outline_complete (★☆☆)
- [S-W-03] Phase 8a → chapter-writer expanded outline field name never specified (★☆☆)
- [S-W-04] Post-revision: no re-run of wiki/recap/lint after chapter revision (★☆☆)
- [S-W-05] generate-elements returns full story_elements in stdout (redundant after PR #71 pattern) (★☆☆)
- [S-W-06] Unimplemented config flags exposed as supported: chapter_min_revisions, enable_final_edit, enable_scrubbing (★☆☆)
- [S-W-07] Scene savepoints created redundantly by both tool and agent instructions (★☆☆)
- [S-W-08] create_chunk.md references enrichment suggestions never provided in tool call (★☆☆)
- [S-I-01] Missing savepoints for individual chunks in chunked outline generation (★☆☆)
- [S-I-02] context-budgeting SKILL.md scoring formula diverges from code (★☆☆)
- [S-I-03] Chapter-writer scene loop steps 5-7 create orphaned savepoints with no load path (★☆☆)
- [S-I-04] critique_runner.py hardcoded threshold 85.0 vs config default 87 — workaround in docs not code (★☆☆)
- [S-I-05] next_chapter_synopsis parameter on scene-writer never populated (★☆☆)

### Divergences

- [D-01] Empty sheets severity: GPT=Warning, Claude+Gemini=Critical → Assessed Critical (downstream poison to entire wiki)
- [D-02] Chunked outline token growth severity: Gemini=Critical, GPT=Warning → Assessed Warning with Critical escalation at >30 chapters
- [D-03] Resume logic severity: GPT=Critical (schema) + Warning (metadata), Claude=Warning → Assessed Warning (robustness gap, not immediate hard failure)
- [D-04] Wiki snapshot budget enforcement bug: Gemini=Critical, others didn't inspect this code path → Singular but high-confidence

### Priority Actions

1. Add LLM generation steps to Phase 5 and Phase 6 before generate-sheet calls
2. Implement chapter quality evaluation — extend critique-runner or build chapter-critique tool
3. Resolve wiki-maintainer invocation granularity (commit to post-chapter)
4. Fix wiki_snapshot.py _enforce_token_budget to drop pages when L1 demotion insufficient
5. Investigate 65k vs 16k context window mismatch
6. Remove previousChunks from expand-chapter — use continuitySummary only
7. Add pipeline_state to story state for resume capability
8. Specify Phase 9 assembly tools, format, output path

### Actions Taken

- Notes written: `.github/notes/audits/2026-04-21-workflow-improvement-synthesis.md`
- Findings to embed into `audits` ChromaDB collection (pending)
