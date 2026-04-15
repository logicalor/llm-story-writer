## Synthesized Code Review — 2026-04-15

**Review Type:** Multi-model synthesis (Claude Opus 4.6 + GPT 5.4 + Gemini 3.1 Pro)
**Branch:** feat/issue-18-outline-planner-subagent
**PR:** #64
**Issue:** #18 — Build Outline Planner Subagent
**Model Agreement Score:** 8/10
**Overall Assessment:** Needs Fixes (minor — no blocking issues)

---

### Synthesis Overview

This PR implements the `outline-planner` subagent and companion `outline-structure` skill, delivering issue #18 across 6 files (~335 insertions). The three models showed strong agreement: all three independently identified the same two config ambiguities (`outline_max_revisions` vs `outline_critique_iterations`, and unenforced `outline_min_revisions`) and the same cosmetic table alignment issue. The main divergence was GPT uniquely flagging a genuine critique-loop responsibility overlap between the orchestrator and planner — verified by manual inspection of the orchestrator agent file.

**Model Agreement Score:** 8/10 — high convergence on substantive findings; divergences limited to singular documentation-level observations that reflect different review emphases rather than contradictions.

---

### Individual Report Summaries

| Model  | Overall Assessment | Unique Focus Areas | Critical Count | Warning Count |
| ------ | ------------------ | ------------------ | -------------- | ------------- |
| Claude | Clean, ready to merge with minor attention | Config completeness (min/max revisions), explicit input contract | 0 | 2 |
| GPT    | Ready with minor revisions | Orchestrator/planner responsibility overlap, pipeline resumability | 0 | 3 |
| Gemini | Ready to merge | Per-criterion floor documentation, critic type verification, expand_outline scope | 0 | 2 |

**Claude** focused on config key coverage — specifically that `outline_min_revisions` is documented but not enforced, and the confusing duality between `outline_max_revisions` and `outline_critique_iterations`. Also suggested an explicit config input list for the agent.

**GPT** uniquely identified the critique-loop responsibility overlap between the orchestrator agent (which still describes running critique directly) and the planner (which now internalises it). Also noted the absence of resume-from-savepoint logic in the agent workflow.

**Gemini** uniquely identified that the per-criterion floor of 75 documented in the skill is not mentioned in the agent workflow, that the 6 critic types lack verification against actual tool implementation, and that `expand_outline` is consumed by the orchestrator, not the planner.

---

### Consensus Findings

#### ★★★ Unanimous Findings (All Three Models Agree)

```
[U-W-01] Ambiguous relationship between outline_max_revisions and outline_critique_iterations
Severity: Warning
Category: Correctness
File: .opencode/skills/outline-structure/SKILL.md
Lines: 145-149
Detail: The skill's Config Reference lists both `outline_max_revisions` (default 3)
  and `outline_critique_iterations` (default 3) as separate config keys. The agent
  exclusively uses `outline_critique_iterations` as its loop bound (Phase 4c). The
  orchestrator's quality gates table uses `outline_max_revisions`. Both default to 3,
  masking the ambiguity under default configuration — but if a user sets them to
  different values, the behavior becomes unpredictable. It is unclear whether these
  are the same concept, aliases, or genuinely distinct controls.
Models: Claude ✓ GPT ✓ Gemini ✓
Suggestion: Clarify in the skill's Config Reference which key is consumed by the
  outline-planner and which by the orchestrator. Either consolidate to one canonical
  key, or document the distinction (e.g., "outline_critique_iterations governs the
  planner's internal loop; outline_max_revisions governs the orchestrator's outer
  revision cap"). A "Used By" column in the config table would resolve this.
```

```
[U-W-02] outline_min_revisions config key not enforced by agent workflow
Severity: Warning
Category: Correctness
File: .opencode/agents/outline-planner.md
Lines: 85-98
Detail: The skill documents `outline_min_revisions` (default 0) as a config key,
  but the agent's Phase 4 exits the critique loop as soon as `should_refine` returns
  false — without checking whether the minimum number of revisions has been completed.
  A user setting `outline_min_revisions: 2` would expect at least two refinement
  passes regardless of quality score, but the current workflow would accept immediately
  if the first critique passes threshold. Under default config (0) this has no impact,
  but becomes a correctness gap when non-default values are used.
Models: Claude ✓ GPT ✓ Gemini ✓ (Gemini noted within its max_revisions finding)
Suggestion: Add a condition in Phase 4d: accept only if `should_refine` is false
  AND iteration >= `outline_min_revisions`. Alternatively, document that
  `outline_min_revisions` is enforced at the orchestrator level, not within the planner.
```

```
[U-S-01] Table separator alignment inconsistency in architecture.md
Severity: Suggestion
Category: Style
File: .github/notes/architecture.md
Lines: 113, 129
Detail: The table header separator dashes were shortened by one character in the
  Agents and Skills tables, creating a minor visual inconsistency with the
  pre-existing style. No rendering impact.
Models: Claude ✓ GPT ✓ Gemini ✓
Suggestion: Cosmetic only — fix or leave as-is. Not actionable.
```

#### ★★☆ Majority Findings (Two of Three Models Agree)

No majority-only findings. All substantive findings were either unanimous or singular.

#### ★☆☆ Singular Findings (Only One Model Reported)

```
[S-W-01] Critique loop responsibility overlap between orchestrator and outline-planner
Severity: Warning
Category: Correctness
File: .opencode/agents/story-orchestrator.md
Lines: 56-62
Detail: The orchestrator's Phase 2 step 3 still describes running the critique loop
  directly ("If enable_outline_critique is true, run critique/revision loop up to
  outline_critique_iterations times: Run critique-runner on the outline…"). However,
  step 1 delegates to the outline-planner, which now internalises the full critique
  loop in its Phase 4. This creates ambiguous ownership — if the orchestrator follows
  its own instructions literally, it would run the critique loop again after the
  planner already did so. The orchestrator agent file was NOT changed in this PR.
Model: GPT
Assessment: GENUINE — verified by manual inspection. The orchestrator agent file
  (.opencode/agents/story-orchestrator.md lines 56-62) contains the duplicate critique
  instructions. This is a real consistency gap introduced by this PR's design choice
  to move critique into the planner without updating the orchestrator. The other two
  models likely missed this because the orchestrator file was not in the diff. Risk:
  medium — the orchestrator would either double-critique (wasting iterations) or
  confuse the agent about which instructions to follow.
Suggestion: Update the orchestrator's Phase 2 to remove step 3 (the direct critique
  loop) and instead note that critique is handled internally by the outline-planner
  subagent. This should be done in this PR to avoid a broken instruction state.
```

```
[S-W-02] Per-criterion floor not documented in agent workflow
Severity: Warning → downgraded to Suggestion
Category: Documentation
File: .opencode/agents/outline-planner.md
Lines: 85-93
Detail: The skill documents a per-criterion floor of 75 (any individual criterion
  below 75 triggers refinement regardless of aggregate score), but the agent's Phase 4
  workflow only mentions the aggregate quality threshold. The agent might misinterpret
  a `should_refine: true` response when the aggregate score exceeds threshold but an
  individual criterion failed.
Model: Gemini
Assessment: Low risk. The `should-refine` tool enforces the per-criterion floor
  internally — the agent doesn't need to implement this check, only understand it.
  Adding a clarifying note in the agent workflow would help but is not a correctness
  issue since the tool does the right thing regardless.
```

```
[S-S-01] Agent lacks explicit config input list
Severity: Suggestion
Category: Documentation
File: .opencode/agents/outline-planner.md
Lines: 4-5
Detail: The agent says it receives "config values from the orchestrator" without
  enumerating which keys it expects. An explicit input contract would reduce ambiguity.
Model: Claude
Assessment: Valid suggestion. Consistent with current convention (chapter-writer also
  lacks this), so addressing it here would set a new precedent. Low priority.
```

```
[S-S-02] Pipeline resumability not addressed in agent workflow
Severity: Suggestion
Category: Documentation
File: .opencode/agents/outline-planner.md
Lines: 18-110
Detail: The agent describes creating savepoints "for resumability" but does not
  explain how to resume from a partial state — e.g., detecting existing savepoints
  and skipping completed phases.
Model: GPT
Assessment: Valid improvement suggestion. The chapter-writer agent describes explicit
  resume logic, so this would improve consistency. Low priority for this PR.
```

```
[S-S-03] Skill documents 6 critic types not verifiable against tool implementation
Severity: Suggestion
Category: Documentation
File: .opencode/skills/outline-structure/SKILL.md
Lines: 126-134
Detail: The skill defines 6 specific critic types (Structure, Character, Continuity,
  Stakes, Originality, Completeness) but these are not cross-referenced with the
  actual critique-runner tool implementation. They may be aspirational.
Model: Gemini
Assessment: Valid concern. Worth verifying during the next integration pass.
  Not blocking for this PR.
```

```
[S-S-04] expand_outline config key consumed by orchestrator, not planner
Severity: Suggestion
Category: Documentation
File: .opencode/skills/outline-structure/SKILL.md
Lines: 153
Detail: The skill's config table includes `expand_outline` (default true) but the
  planner never references it — this key is consumed by the orchestrator's Phase 8a.
  Including it in the skill's config table without a "Used By" annotation could
  mislead the planner agent into thinking it should act on this key.
Model: Gemini
Assessment: Valid. A "Used By" column in the config table would resolve this and
  the U-W-01 finding simultaneously.
```

---

### Divergence Analysis

```
[D-01] Topic: Orchestrator critique loop overlap
Claude says: (not flagged)
GPT says: Warning — orchestrator Phase 2 step 3 still describes running the critique
  loop directly, creating dual ownership with the planner's internal Phase 4.
Gemini says: (not flagged)
Assessment: GPT is correct. Verified by manual inspection of
  .opencode/agents/story-orchestrator.md lines 56-62. The orchestrator file was not
  in the diff, which explains why Claude and Gemini missed it — they likely reviewed
  only changed files. GPT performed a broader contextual check. This is a genuine
  consistency gap that should be addressed in this PR.
Resolution: Elevated to recommended action. The orchestrator's Phase 2 should be
  updated to defer critique responsibility to the planner.
```

```
[D-02] Topic: Whether outline_min_revisions is a standalone finding
Claude says: Separate Warning (W-01) focused entirely on min_revisions enforcement
GPT says: Separate Warning (W-02) focused entirely on min_revisions enforcement
Gemini says: Secondary mention within the max_revisions/critique_iterations finding (W-02)
Assessment: Same substance, different classification. Claude and GPT correctly
  separated it as a distinct issue since min_revisions and the max/iterations ambiguity
  have different root causes and different fixes. Classified as Unanimous in synthesis.
Resolution: No impact — finding captured as U-W-02.
```

```
[D-03] Topic: Per-criterion floor documentation
Claude says: (not flagged)
GPT says: (not flagged)
Gemini says: Warning — agent workflow should mention the 75 per-criterion floor
Assessment: Gemini raises a valid point, but this is a documentation improvement,
  not a correctness issue. The tool enforces the floor regardless of what the agent
  understands. The 2-vs-1 split and low runtime impact justify downgrading to Suggestion.
Resolution: Included as singular suggestion [S-W-02], downgraded from Warning.
```

---

### Recommended Actions (Prioritized)

```
1. [S-W-01] ★☆☆ Fix: Update orchestrator Phase 2 to remove duplicate critique loop
   instructions — defer to outline-planner (Warning — 1 model, verified genuine)
2. [U-W-01] ★★★ Clarify: Document which config key (outline_max_revisions vs
   outline_critique_iterations) is consumed by planner vs orchestrator (Warning — all agree)
3. [U-W-02] ★★★ Fix: Add outline_min_revisions enforcement to Phase 4d, or
   document it as orchestrator-level (Warning — all agree)
4. [U-S-01] ★★★ Skip: Table alignment — cosmetic only (Suggestion — all agree)
5. [S-W-02] ★☆☆ Consider: Add per-criterion floor note to agent workflow (Suggestion — 1 model)
6. [S-S-01] ★☆☆ Consider: Add explicit config input list to agent (Suggestion — 1 model)
7. [S-S-02] ★☆☆ Consider: Add resume-from-savepoint logic (Suggestion — 1 model)
8. [S-S-03] ★☆☆ Defer: Verify critic types against tool implementation (Suggestion — 1 model)
9. [S-S-04] ★☆☆ Consider: Add "Used By" column to skill config table (Suggestion — 1 model)
```

**Note:** Action #1 is ranked highest despite being singular because it was verified as genuine and represents a broken instruction state — the orchestrator would attempt to run critique both via its own steps AND via the planner. Actions #2 and #3 are config documentation gaps with no runtime impact under default values.

---

### Finding Counts by Consensus

| Consensus         | Critical | Warning | Suggestion |
| ----------------- | -------- | ------- | ---------- |
| ★★★ Unanimous     | 0        | 2       | 1          |
| ★★☆ Majority      | 0        | 0       | 0          |
| ★☆☆ Singular      | 0        | 1       | 4          |

### Key Findings

- [U-W-01] Config ambiguity: outline_max_revisions vs outline_critique_iterations (★★★)
- [U-W-02] outline_min_revisions not enforced in agent workflow (★★★)
- [S-W-01] Orchestrator Phase 2 still describes critique loop — conflicts with planner (★☆☆, verified)

### Divergences

- [D-01] Orchestrator overlap — GPT only but verified genuine, elevated to action #1
- [D-02] min_revisions classification — cosmetic difference, substance unanimous
- [D-03] Per-criterion floor — Gemini only, downgraded from Warning to Suggestion

### Actions Required

- Findings requiring fixes: 3 (S-W-01, U-W-01, U-W-02)
- Findings deferred: 4 (S-S-01 through S-S-04)
- Findings skipped: 1 (U-S-01 — cosmetic)
