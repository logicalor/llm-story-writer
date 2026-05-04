## Synthesized Audit — 2026-05-04

**Audit Type:** Multi-model synthesis (Claude Sonnet 4.6 · GPT · Gemini)
**Audit Scope:** Architectural relationship between wiki maintenance, character/setting sheets, and chapter recaps
**Model Agreement Score:** 8/10
**Overall Health:** Needs Attention — mid-migration with two active quality defects
**Development Stage:** Phase 5 complete, Phase 6 partial (incomplete entity coverage), Phase 7c implemented, Phase 7d not wired

### User Hypothesis Verdict

**Confirmed by all three models.** The three-way split between character/setting sheets, recaps, and the wiki is an antipattern that has already caused measurable data divergence. Consolidation into wiki maintenance (with ChromaDB searchability) is the correct architectural direction. ADR 004 already mandated this; the implementation has not caught up.

### Finding Counts by Consensus

| Consensus         | Critical | Warning | Info/Suggestion |
| ----------------- | -------- | ------- | --------------- |
| ★★★ Unanimous     | 2        | 1       | 0               |
| ★★☆ Majority      | 1        | 3       | 0               |
| ★☆☆ Singular      | 0        | 1       | 1               |

### Key Findings

- [U-C-01] Entity coverage gap: wiki missing 2 characters + 2 settings vs. sheet store (★★★) — active now
- [U-C-02] Recap event data not in wiki/ChromaDB — temporal dimension invisible to retrieval pipeline (★★★)
- [U-W-01] Three-way split confirmed antipattern — ADR 004 mandate not yet completed (★★★)
- [M-C-01] Parallel per-chapter mutation: wiki-maintainer AND sheet evolver both run post-chapter (★★☆)
- [M-W-01] Chapter-writer injects both wiki context AND raw sheet context simultaneously (★★☆)
- [M-W-02] Recap has richer event structure than wiki timeline — migration must expand schema first (★★☆)
- [M-W-03] ADR 004 still "Proposed"; Phase 6 spec contradicts actual implementation (★★☆)
- [S-I-01] ChromaDB surface fragmentation: wiki collection vs. RAG collection (★☆☆)
- [S-I-02] Long-term: Phase 5 could natively output wiki pages, skipping Phase 6 bridge (★☆☆)

### Divergences

- [D-01] Wiki bootstrap mechanism: Claude says re-extracts from outline text (misses entities not in outline); GPT says reads sheet files but produces incomplete coverage; Gemini accepted spec claim that Phase 6 isn't wired. All agree on EFFECT (coverage gap). Cause needs direct code inspection of `orchestrator.py` wiki-bootstrap block.
- [D-02] Sheet retirement aggressiveness: Claude/GPT agree — freeze sheets after bootstrap, retire per-chapter evolution. Gemini suggests Phase 5 should output wiki pages natively (longer-term). No genuine direction disagreement.

### Recommended Priority Actions

1. Fix wiki bootstrap mechanism — ensure the initial-populate path iterates all entities in `characters/*.json` and `settings/*.json` as its entity source, guaranteeing complete wiki coverage regardless of outline text prominence
2. Push recap event data into wiki event pages — expand `_schema.md` event frontmatter to carry timestamp, participants, importance, emotional state, causal context
3. Stop per-chapter sheet evolution (CharacterEvolverAgent / SettingEvolverAgent); wiki-maintainer owns post-chapter entity state
4. Invert chapter-writer fallback guard — wiki-snapshot primary, raw sheets exception-path only
5. Update ADR 004 status → Accepted; rewrite Phase 6 and Phase 7d spec sections

### Actions Taken

- Notes written: `.github/notes/audits/2026-05-04-wiki-consolidation-synthesis.md`
- Issues created: pending user approval
