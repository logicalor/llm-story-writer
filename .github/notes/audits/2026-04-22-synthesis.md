# Synthesized Audit — 2026-04-22

**Audit Type:** Multi-model synthesis (Claude Sonnet 4.6 + GPT 5.4 + Gemini 3.1 Pro Preview)
**Audit Focus:** Subagent infrastructure vs. tools/workflow — candidates for fine-grained subagent expansion
**Model Agreement Score:** 8/10
**Overall Health:** Healthy — working pipeline with clear expansion path
**Development Stage:** Production-ready core (Phases 1–7 implemented); Phase 9 (final-edit/scrubbing) unimplemented

---

## Synthesis Overview

The llm-story-writer's five-subagent architecture is structurally sound and correctly delegates the three most expensive creative loops — outline generation, character/setting sheet production, and scene writing. However, the orchestrator remains disproportionately responsible for the per-chapter quality loop (Phase 7f), which is the pipeline's most complex non-delegated logic. All three models converged strongly on `quality-reviewer` and `final-editor` as the highest-priority additions, and all three independently identified the depth-1 nesting constraint (from PR #70) as a hard architectural requirement for any expansion. Agreement across models was high (8/10), with meaningful divergence only on three candidates.

**Model Agreement Score:** 8/10

---

## Individual Report Summaries

| Model  | Overall Assessment | Unique Focus Areas | Critical Count | Warning Count |
| ------ | ------------------ | ------------------ | -------------- | ------------- |
| Claude | Most architecturally detailed; strong nesting-risk analysis | Raw-chapter RAG continuity auditor; `enable_scrubbing` as separate agent; quality-reviewer depth-2 re-trigger risk | 0 | 6 |
| GPT    | Most concerned with infrastructure hygiene before expansion; noted registry/doc drift | Agent registry documentation drift as prerequisite; chapter handoff synthesizer concept | 0 | 5 |
| Gemini | Most opinionated/concise; strongest on quality-reviewer and final-editor; most conservative on specialist subagents | Pre-flight structuring (Phase 1.5 interactive clarification); character-voice-analyst as critic persona not subagent | 0 | 4 |

---

## Development Stage (Consensus)

| Phase                                    | Status      | Completion         | Agreement |
| ---------------------------------------- | ----------- | ------------------ | --------- |
| Phase 1–6 (Init → Wiki Population)       | Done        | All phases working | Unanimous |
| Phase 7 (Per-chapter loop)               | Done        | Working, overloaded orchestrator | Unanimous |
| Phase 8 (Assembly)                       | Done        | Tool call, no subagent | Unanimous |
| Phase 9 (Final edit / scrubbing)         | Not Started | Config flags exist, no implementation | Unanimous |
| Subagent registry/documentation          | Needs work  | Drift between files | Majority (GPT/Claude) |

---

## Consensus Findings

### ★★★ Unanimous Findings (All Three Models Agree)

```
[U-W-01] quality-reviewer subagent is the highest-priority addition
Severity: Warning
Category: Architecture
Detail: Phase 7f is a genuine multi-step workflow — run critics (critique-runner:
  run-critics) → parse scores → evaluate should-refine against chapter_quality and
  chapter_min_revisions thresholds → generate feedback → revise loop up to
  chapter_max_revisions → conditionally re-trigger Phases 7c, 7d, and 7e for the
  revised chapter. This logic is more complex than any existing subagent's workflow
  and currently sits entirely in the orchestrator, increasing context bloat and
  instruction drift risk across a 25-chapter loop.
Models: Claude ✓  GPT ✓  Gemini ✓
Impact: Largest single reduction in orchestrator complexity; adds audit trail for
  revision decisions; clean scope boundary with orchestrator.
```

```
[U-W-02] final-editor implements a planned but unimplemented feature
Severity: Warning
Category: Architecture
Detail: enable_final_edit is a config flag documented in Phase 7f with "planned
  feature — not yet implemented." No implementation path exists. A final-editor
  subagent operating on the assembled manuscript would perform cross-chapter prose
  polish, voice consistency, and pacing review — a qualitatively different task from
  the per-chapter quality evaluation in Phase 7f. Must operate at prose/paragraph
  scope only; wholesale chapter rewriting defeats the purpose.
Models: Claude ✓  GPT ✓  Gemini ✓
Impact: Activates a committed feature; adds a manuscript-level quality pass that
  no existing agent or tool provides.
```

```
[U-I-03] manuscript-assembler subagent should not be created
Severity: Info
Category: Architecture
Detail: story-assembler is a single deterministic tool call — it reads chapter
  savepoints from disk and writes output/story.md. No LLM reasoning, no multi-step
  orchestration. An agent wrapper adds dispatch overhead for zero functional gain.
  Remains correctly a tool-only responsibility.
Models: Claude ✓  GPT ✓  Gemini ✓
Impact: Confirms current design is correct for Phase 8.
```

```
[U-W-04] Orchestrator is overloaded in the per-chapter loop
Severity: Warning
Category: Architecture
Detail: Phases 7a (expand-chapter loop with continuity state threading), 7d (recap
  pipeline), 7e (wiki lint), and 7f (critique revision loop) are all direct
  orchestrator tool calls. The orchestrator simultaneously acts as scheduler,
  continuity tracker, recap coordinator, lint dispatcher, and quality gate
  controller — a concentration of branching logic that increases the risk of
  context compaction silently corrupting state across 25 chapters.
Models: Claude ✓  GPT ✓  Gemini ✓
Impact: Core architectural weakness; each phase extracted to a subagent reduces
  per-chapter orchestrator context by an estimated 20–40%.
```

```
[U-W-05] Depth-1 nesting constraint must be enforced for all new subagents
Severity: Warning
Category: Architecture
Detail: The depth-2 nested dispatch pattern (orchestrator → subagent → sub-subagent)
  caused the VS Code UI freeze resolved in PR #70. All new subagents must be
  dispatched directly from story-orchestrator at depth-1. No subagent may dispatch
  another subagent. This specifically constrains: quality-reviewer must call
  critique-runner as a tool (not dispatch scene-revisor or wiki-maintainer as
  sub-agents); final-editor must call scene-writer as a tool; character-voice-analyst
  must be an orchestrator-level dispatch, not a chapter-writer sub-dispatch.
Models: Claude ✓  GPT ✓  Gemini ✓
Impact: Hard architectural constraint; violating it causes known stability failure.
```

---

### ★★☆ Majority Findings (Two of Three Models Agree)

```
[M-W-01] chapter-outline-expander should be introduced for Phase 7a
Severity: Warning
Category: Architecture
Detail: Phase 7a repeats outline-generator:expand-chapter for every chapter,
  carrying continuitySummary forward across iterations. This state is currently
  managed inline by the orchestrator — if the orchestrator's context is compacted
  under high token pressure across a 25-chapter loop, the continuity summary is
  silently dropped. A chapter-outline-expander subagent would own the full loop
  across all wanted_chapters, making continuity tracking explicit and reducing
  orchestrator working memory.
Models: GPT ✓  Gemini ✓  Claude ✗
Dissenting view: Claude rates this Consider/Low, arguing per-iteration logic is
  minimal and only warrants a subagent if continuity processing becomes more complex.
Impact: Modest architectural cleanliness; meaningful resilience improvement for
  long stories where context compaction risk is highest.
```

```
[M-W-02] story-planner adds macro narrative arc analysis currently absent
Severity: Warning
Category: Architecture
Detail: outline-planner generates structurally complete outlines but does not
  evaluate dramatic arc quality — rising action, climax placement, pacing
  distribution, thematic resolution. A story-planner operating after outline-planner
  (Phase 2 post-gate) but before Phase 3 human approval could evaluate arc quality
  using the six existing outline_review/ prompts (literary-fiction-reviewer,
  publishing-acquisitions-editor, etc.) and surface structural problems at the
  cheapest point in the pipeline — before any scene generation — rather than
  discovering them at chapter 18. Should be advisory, not blocking (present
  assessment to user at Phase 3 rather than introducing a second automated
  revision loop).
Models: Claude ✓  Gemini ✓  GPT ✗
Dissenting view: GPT rates this Consider/Medium — agrees on value but positions
  it as second-wave after quality control stabilises.
Impact: Catches structural arc problems before expensive generation begins.
```

```
[M-I-03] consistency-checker has conditional architectural value
Severity: Info
Category: Architecture
Detail: In its current scope, Phase 7e is a single wiki-lint:check-chapter call —
  no subagent wrapping justified. The candidate becomes worthwhile only if scope
  expands to include cross-narrative semantic analysis: combining wiki-search,
  rag-query (ChromaDB over raw chapter embeddings), and wiki-read to detect drift
  that deterministic pattern matching misses. Examples: character eye colour stated
  in chapter 2 and contradicted in chapter 15 but never explicitly encoded as a
  wiki entity property; personality trait drift not reflected in wiki updates.
Models: Claude ✓  Gemini ✓  GPT ✗
Dissenting view: GPT rates Recommend/High — more enthusiastic about immediate value.
Impact: Genuine value only with expanded scope; premature if wrapping only the
  existing wiki-lint call.
```

```
[M-I-04] recap-writer is low priority — existing tool coverage is adequate
Severity: Info
Category: Architecture
Detail: recap-manager:generate already encapsulates a multi-step pipeline internally
  (extract events → assign timing → enrich details → format → filter), each stage
  with its own savepoint. The orchestrator calls this as a single operation. There
  is no multi-step orchestration at the agent level and no LLM reasoning required
  of the orchestrator. Wrapping in a subagent would add dispatch overhead without
  enabling new capability — unless recaps become durable multi-purpose continuity
  artifacts used for planning purposes, not just retrospective summaries.
Models: GPT ✓  Gemini ✓  Claude ✗
Dissenting view: Claude says Skip explicitly. GPT/Gemini say Consider but with
  Low/Medium priority.
Impact: Current design is adequate; revisit if recap requirements grow.
```

```
[M-I-05] scene-revisor should not be created
Severity: Info
Category: Architecture
Detail: chapter-writer already manages scene-level revision internally via
  scene-writer:revise. Introducing a scene-revisor dispatched from within
  chapter-writer would create depth-2 nesting (finding [U-W-05]). Dispatching
  from the orchestrator would require scene content to be passed out of
  chapter-writer to the orchestrator and back in — breaking chapter-writer's clean
  encapsulation. Quality-reviewer (at chapter granularity) covers the functional
  requirement without these risks.
Models: Claude ✓  Gemini ✓  GPT ✗
Dissenting view: GPT rates Consider/Medium but recommends deferral.
Impact: Skip; overlap with quality-reviewer makes this redundant.
```

---

### ★☆☆ Singular Findings (Only One Model Reported)

```
[S-I-01] Pre-flight structuring: Phase 1.5 interactive prompt clarification (Gemini)
Severity: Info
Category: Architecture
Detail: Gemini uniquely identifies value in an interactive clarification phase
  before outlining begins — testing the story prompt's "narrative carrying capacity,"
  asking targeted questions about world rules, stakes, tone, and genre expectations.
  This would reduce outline planner churn from under-specified prompts. Currently
  the pipeline proceeds directly from raw prompt → analyze-prompt with no user
  input checkpoint.
Model: Gemini
Assessment: Genuinely valuable for complex or ambiguous prompts; may be overkill
  for simple genre fiction. Implementation would require an interactive agent mode
  rather than a batch-safe tool call. Low risk; moderate value.
```

```
[S-I-02] Agent registry documentation drift exists today (GPT)
Severity: Info
Category: Documentation
Detail: GPT uniquely observes that the existing agent infrastructure already shows
  documentation drift — architecture notes describe only three primary subagents while
  five agent files exist; the orchestrator's registered subagent permissions may not
  be fully current. Before expanding the subagent roster, the registry, permissions,
  orchestrator instructions, and architecture documentation should agree.
Model: GPT
Assessment: Likely a genuine finding. character-sheet-generator exists as an agent
  file and the orchestrator dispatches it, but its addition may not be reflected in
  all documentation. Low effort to verify and fix; worthwhile as a pre-expansion
  hygiene step.
```

```
[S-I-03] Chapter handoff synthesizer: durable per-chapter continuity artifact (GPT)
Severity: Info
Category: Architecture
Detail: GPT uniquely proposes a chapter handoff synthesizer — after each accepted
  chapter, generate a compact structured artifact capturing: resolved beats, newly
  introduced obligations, active tensions, timeline movement, and character state
  deltas. This would be richer than the existing recap (which focuses on narrative
  summary) and inform Phase 7a outline expansion more effectively. Currently the
  orchestrator threads continuitySummary from expand-chapter output, which is
  structurally implicit rather than explicitly managed.
Model: GPT
Assessment: High qualitative value for long-form consistency; complements both
  chapter-outline-expander and consistency-checker candidates. Implementation is
  moderate complexity (new structured output format; new tool operation or story-state
  schema extension).
```

```
[S-I-04] Cross-chapter continuity auditor using raw chapter RAG (Claude)
Severity: Info
Category: Architecture
Detail: Claude uniquely identifies a gap in the wiki-based approach: wiki pages are
  updated after each chapter, but they lag by one chapter at generation time, and they
  only capture facts explicitly extracted by wiki-maintainer. Fine-grained factual
  details (character eye colour, specific dates, minor world-rule statements) may
  never be encoded as wiki entity properties. A continuity auditor querying
  ChromaDB over raw chapter text embeddings (not wiki pages) via rag-query could
  catch contradictions the wiki-based consistency checking misses.
Model: Claude
Assessment: Addresses a genuine blind spot in the current architecture. Requires
  a ChromaDB collection indexed over raw chapter text, separate from the wiki
  collection. Technically feasible with existing rag-query tool; primarily a
  prompting and orchestration problem.
```

```
[S-I-05] Prose scrubbing agent for enable_scrubbing (Claude)
Severity: Info
Category: Architecture
Detail: Claude notes that enable_scrubbing is a separate planned config flag from
  enable_final_edit, and the two features have distinct scopes: final-edit is
  macro-level prose quality; scrubbing is sentence/paragraph-level (repetitive
  phrases, adverb overuse, filter-word removal, show-vs-tell ratio). A dedicated
  prose-scrubber subagent would implement enable_scrubbing without contaminating
  the final-editor's higher-level concerns.
Model: Claude
Assessment: Correct distinction — these are meaningfully different tasks. Implement
  scrubbing as a separate feature once final-editor is in place. Could run both
  per-chapter (Phase 7.5) and manuscript-wide (Phase 9).
```

---

## Divergence Analysis

```
[D-01] Topic: character-voice-analyst — subagent vs. critic persona
Claude says: Recommend as a dedicated subagent running between Phase 7b and 7f.
  Rationale: cross-chapter analysis (loading prior chapter text via rag-query) is
  beyond what a single-pass critic inside critique-runner can do.
GPT says: Recommend as a triggerable specialist invoked on demand by quality-reviewer
  or consistency-checker, not as an always-on stage per chapter.
Gemini says: Skip as a subagent. The chapter-character-consistency.md prompt already
  exists in chapter_review/ and should be integrated as a critic persona within
  critique-runner rather than becoming a new agent.
Assessment: Gemini's argument is correct for the simpler case (intra-chapter
  consistency within current chapter vs. wiki state). Claude and GPT's arguments
  hold for the harder case (multi-chapter voice drift tracked across raw text).
  The 2:1 split favors a dedicated subagent, but the graduation path makes more
  sense: integrate as a critique-runner mode first (Gemini), then graduate to a
  dedicated subagent when cross-chapter analysis is needed (Claude/GPT).
Resolution: Implement as enhanced critic mode in critique-runner initially. Treat
  as a dedicated subagent candidate once multi-chapter voice drift is confirmed
  as a production quality problem.
```

```
[D-02] Topic: chapter-outline-expander — priority assessment
Claude says: Consider / Low. Per-iteration logic is minimal; only becomes worthwhile
  if continuity processing grows more complex.
GPT says: Recommend / High. Removing continuity state from orchestrator's working
  memory is architecturally important; positions for cleaner future enrichment.
Gemini says: Recommend / Medium. Improves connective tissue between chapters.
Assessment: 2:1 in favour of Recommend. Claude's caution is valid for the current
  implementation but underweights the context compaction risk in long stories (25+
  chapters). GPT's High priority may be slightly aggressive — the functional risk
  is real but not an immediate blocker. Medium priority with second-wave timing
  is the most defensible position.
Resolution: Recommend / Medium. Introduce as part of second-wave expansion after
  quality-reviewer is stable.
```

```
[D-03] Topic: consistency-checker — priority and immediate value
Claude says: Consider / Medium. Only worth building with expanded semantic scope;
  single wiki-lint delegation is insufficient justification.
GPT says: Recommend / High. Sees genuine analytical owner for coherence problems
  that currently has no clear home.
Gemini says: Consider / Medium. Only adds value if it interprets linting failures
  and proposes fixes, not just reports errors.
Assessment: Claude and Gemini's conditional framing is more precise. GPT's High
  rating assumes a broader scope that isn't yet defined. The finding is best
  treated as "worth building if defined with expanded scope."
Resolution: Consider / Medium. Start by defining expanded scope (what semantic
  analysis beyond wiki-lint). Build only once scope is concrete.
```

---

## Deviations from Plan (Consensus)

| Plan says | Code does | Models flagging |
|-----------|-----------|-----------------|
| `enable_final_edit` is a planned feature | No implementation exists; config flag, no agent | Claude ✓ GPT ✓ Gemini ✓ |
| `enable_scrubbing` is a planned feature | No implementation exists; config flag, no agent | Claude ✓ (only Claude flagged explicitly) |
| Quality loop should be delegated per hybrid architecture | Phase 7f is orchestrator-direct tool calls | Claude ✓ GPT ✓ Gemini ✓ |

---

## Risk Assessment (Synthesized)

| Risk | Severity | Models | Mitigation |
|------|----------|--------|------------|
| Depth-2 nesting instability | High | All | All new subagents dispatch from orchestrator at depth-1 only. No subagent dispatches subagents. quality-reviewer calls critique-runner as a tool, not as a sub-dispatch |
| quality-reviewer re-triggers 7c/7d/7e creating depth issues | Medium | Claude | quality-reviewer returns `requires_post_processing: true` flag; orchestrator re-triggers downstream phases rather than quality-reviewer dispatching them |
| Context overflow in quality-reviewer across revision loop | Medium | Claude | Reference chapter content via savepoint key; summarise critique output rather than accumulating raw text across revisions |
| final-editor scope creep to wholesale chapter rewriting | Medium | Claude | final-editor skill must constrain to prose/paragraph scope; prohibit chapter replacement; operate chapter-by-chapter not on undifferentiated manuscript |
| State desynchronisation after revision | Medium | GPT/Gemini | Only commit chapter state after acceptance; enforce canonical post-revision order: accept → wiki update → recap → lint → savepoint |
| Documentation drift amplified by more agents | Low | GPT | Fix registry/permission/doc alignment before expansion; add one machine-checkable registry source of truth |

---

## Recommended Actions (Prioritized)

```
1. [U-W-01] ★★★ Create quality-reviewer subagent — extract Phase 7f
   Phase 7f critique loop → dedicated subagent. Tools: critique-runner, scene-writer
   (revise), story-state, savepoint-mgr. Returns accepted chapter + best score.
   Orchestrator re-triggers 7c/7d/7e on acceptance.

2. [U-W-02] ★★★ Create final-editor subagent — implement enable_final_edit
   Post-assembly prose pass. Tools: scene-writer (revise), story-state, rag-query.
   New prompts required. Constrain to sentence/paragraph scope only.

3. [S-I-02] ★☆☆ Audit and fix agent registry documentation drift
   Verify orchestrator registered subagent list matches all agent files; update
   architecture documentation to reflect all five current subagents.

4. [M-W-01] ★★☆ Create chapter-outline-expander — Phase 7a loop ownership
   Second-wave. Owns expand-chapter loop across all chapters with explicit
   continuity state management. Reduces orchestrator working memory risk for
   long stories.

5. [M-W-02] ★★☆ Create story-planner — post-Phase 2 arc analysis gate
   Second-wave. Uses outline_review/ prompts to evaluate dramatic structure.
   Advisory output to Phase 3 human gate; does not introduce automated revision loop.

6. [D-01] ★★☆ Enhance critique-runner with character-voice mode first
   Integrate chapter-character-consistency.md as a critique-runner mode before
   creating a dedicated subagent. Graduate to dedicated subagent only once
   cross-chapter analysis is needed.

7. [M-I-03] ★★☆ Define and build consistency-checker with expanded scope
   Only worth building if scope includes RAG-based cross-narrative semantic analysis.
   Define scope first; build second.

8. [S-I-04] ★☆☆ Consider raw-chapter RAG continuity auditor
   Index raw chapter text in ChromaDB collection; query via rag-query to catch
   fine-grained facts never encoded as wiki properties. High value if continuity
   errors are observed in practice.

9. [S-I-05] ★☆☆ Create prose-scrubber subagent — implement enable_scrubbing
   Separate from final-editor. Sentence/paragraph-level quality: adverb density,
   repetitive phrasing, filter words, show-vs-tell. Can run per-chapter and
   manuscript-wide.
```

---

## Finding Counts by Consensus

| Consensus     | Critical | Warning | Info |
| ------------- | -------- | ------- | ---- |
| ★★★ Unanimous | 0        | 4       | 1    |
| ★★☆ Majority  | 0        | 2       | 3    |
| ★☆☆ Singular  | 0        | 0       | 5    |

---

## Actions Taken

- Notes written: `.github/notes/audits/2026-04-22-synthesis.md`
- ChromaDB: findings embedded into `audits` collection (IDs: `audit-2026-04-22-*`)
