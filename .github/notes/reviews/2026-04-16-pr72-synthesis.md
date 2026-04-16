# Synthesized Code Review — PR #72

**Branch:** `feat/issue-25-context-budgeting-wiki-skills`
**Review Type:** Multi-model synthesis (Claude Opus 4.6 + GPT 5.4 + Gemini 3.1 Pro)
**Date:** 2026-04-16

---

## Synthesis Overview

This PR adds two new OpenCode skills (`context-budgeting` and `wiki-conventions`), extends `wiki-maintenance` with alias edge cases and a ConStory-Bench error taxonomy, and updates documentation across feature docs and `opencode.json`. All three models agreed the PR is well-structured, additive, and faithfully reproduces ADR source material. Agreement was high — every finding from every model was corroborated by at least one other model, with the exception of one Claude-only finding regarding the wiki-maintainer agent body text. The highest-confidence findings are a stale prose count in `docs/features/story-orchestrator.md`, an internal token budget ambiguity in the context-budgeting skill, and unrelated test changes bundled into the branch.

**Model Agreement Score:** 8/10 — All three models identified the same core issues. Disagreements were limited to severity classification and one model-specific finding. No contradictory assessments.

---

## Individual Report Summaries

| Model  | Overall Assessment | Unique Focus Areas | Critical Count | Warning Count |
| ------ | ------------------ | ------------------ | -------------- | ------------- |
| Claude | Ready after fixing two doc warnings | Agent body text consistency; maintenance risk of duplicated tables | 0 | 3 |
| GPT    | Ready after one-line fix | Detailed verification checklist; ADR value spot-checks; commit-level analysis | 0 | 1 |
| Gemini | Ready after clarifying budget figure | Token budget correctness impact on agent behavior; comprehensive ADR verification table | 0 | 2 |

- **Claude** provided the most findings (5 total) and was the only model to flag the wiki-maintainer agent body text omission. Claude also uniquely identified the duplicated entity type table as a maintenance risk, and correctly characterized the test changes as substantive (new methods, not just formatting).
- **GPT** was the most conservative in finding count (3 total) and severity assignment. GPT ran the most thorough verification checklist (11 items across all review phases) and verified ADR values at the line level. GPT initially characterized the test changes as "reformatting," which understates the actual additions.
- **Gemini** uniquely elevated the 15K/25K budget ambiguity to Warning severity with a Correctness category, arguing an agent could under-allocate context tokens. Gemini also provided a structured verification summary table (13 checks) and correctly identified the test changes as substantive.

---

## Consensus Findings

### ★★★ Unanimous Findings (All Three Models Agree)

```
[U-W-01] Stale skill count for wiki-maintainer in story-orchestrator.md
Severity: Warning
Category: Documentation
File: docs/features/story-orchestrator.md
Lines: 138-141
Detail: The wiki-maintainer subsection states "The agent uses one skill:" and lists only
wiki-maintenance, then adds wiki-conventions in a separate sentence ("The agent also has
access to the wiki-conventions skill..."). This creates a false distinction — opencode.json
registers both skills equally in the skills array. The phrasing is also inconsistent with
how every other agent's skills are listed in the same file (chapter-writer says "three
skills:" with a bullet list, outline-planner says "two skills:" with a bullet list). The
companion file docs/features/wiki-maintainer.md correctly says "uses two skills:" with
both listed, making the inconsistency between the two docs files apparent.
Models: Claude ✓ (W-01, Warning) GPT ✓ (W-01, Warning) Gemini ✓ (S-01, Suggestion)
Severity consensus: 2/3 Warning — adopted as Warning
Suggestion: Change "uses one skill:" to "uses two skills:" and list both skills as bullet
points in the same list, removing the separate "also has access to" paragraph. Match the
pattern used for other subagents in the same file.
```

```
[U-W-02] Internal token budget ambiguity — 15K vs 25K in context-budgeting skill
Severity: Warning
Category: Documentation
File: .opencode/skills/context-budgeting/SKILL.md
Lines: 22-28, 82-83
Detail: The token budget table allocates ~25,000 tokens to "Story context (loaded by tool)"
but Stage 2 references "the ~15K token budget for the story context portion of the window."
The phrase "for the story context portion" reads as if the entire story context budget is
15K, contradicting the 25K in the table. In reality, the ~15K (from ADR 005) is the
wiki-page sub-allocation within the larger ~25K story context budget — the remaining ~10K
covers the chapter outline and recap. All three models identified this ambiguity; Gemini
raised it to Warning severity arguing it could cause an agent to under-allocate context.
Both values are faithfully reproduced from their respective ADRs (ADR 002 for 25K, ADR 005
for 15K), but in a single skill document the apparent contradiction is misleading.
Models: Claude ✓ (S-02, Suggestion) GPT ✓ (S-01, Suggestion) Gemini ✓ (W-02, Warning)
Severity consensus: 2/3 Suggestion, but elevated to Warning — Gemini's reasoning that an
agent consuming this skill could under-allocate tokens is compelling. The ambiguity has a
functional correctness risk, not just a readability concern.
Suggestion: Clarify the line to: "Pages are sorted by relevance score and assigned detail
levels top-down within the ~15K wiki-page allocation of the ~25K story context budget."
This preserves the ADR 005 figure while disambiguating from the budget table.
```

```
[U-W-03] Unrelated test changes bundled into issue-25 branch
Severity: Warning
Category: Style
File: tests/unit/test_compaction_plugin.py
Lines: 1, 72-110
Detail: The branch is for issue #25 (context-budgeting and wiki-conventions skills), but
the diff includes changes to test_compaction_plugin.py: the docstring was changed from
"Verification tests for Issue #23" to "Issues #23, #68", and four new test methods were
added (test_plugin_context_interface_defined, test_compaction_input_interface_defined,
test_compaction_output_interface_defined, test_plugin_export_uses_typed_parameters). These
test compaction plugin interfaces related to issues #23/#68, unrelated to issue #25.
Bundling unrelated changes makes the branch harder to review, revert, and bisect.
Models: Claude ✓ (W-03, Warning) GPT ✓ (S-02, Suggestion) Gemini ✓ (W-01, Warning)
Severity consensus: 2/3 Warning — adopted as Warning. Note: GPT characterized these as
"reformatted assert statements" (cosmetic whitespace), while Claude and Gemini correctly
identified substantive new test method additions. The changes are clearly non-cosmetic.
Suggestion: Move the test changes to their own branch/PR under the relevant issue (#23 or
#68), or at minimum acknowledge the inclusion in the commit message with rationale.
```

### ★★☆ Majority Findings (Two of Three Models Agree)

```
[M-S-01] Duplicated entity type table across wiki-conventions and wiki-maintenance skills
Severity: Suggestion
Category: Documentation
File: .opencode/skills/wiki-conventions/SKILL.md
Lines: 42-62
Detail: The 12-row entity type table with frontmatter field specifications appears
identically in both wiki-conventions/SKILL.md and wiki-maintenance/SKILL.md. Similarly,
detail level guidelines (L1/L2/L3 definitions and token targets) appear across multiple
skills. Both models that flagged this acknowledged the deliberate design choice — skills
are self-contained so agents loading a subset get complete reference material — but noted
the maintenance risk: any future change to entity types or detail levels must be
synchronised across all files.
Models: Claude ✓ (S-01) Gemini ✓ (S-02) GPT ✗
Dissenting view: GPT did not report this finding but noted in its verification checklist
that "skill files are complementary" — it acknowledged the duplication implicitly but did
not consider it an issue worth flagging.
Suggestion: Add a sync comment at the top of duplicated sections noting the canonical
source and which files must be kept in sync, e.g.:
<!-- Canonical: wiki-conventions/SKILL.md. Keep in sync with wiki-maintenance/SKILL.md -->
```

### ★☆☆ Singular Findings (Only One Model Reported)

```
[S-W-01] Wiki-maintainer agent body text does not list wiki-conventions skill
Severity: Warning
Category: Documentation
File: .opencode/agents/wiki-maintainer.md
Lines: 22-23
Detail: The wiki-maintainer agent definition lists only wiki-maintenance in its "## Skills"
section, but opencode.json now declares both wiki-maintenance and wiki-conventions in the
skills array. While OpenCode loads skills from config automatically, the agent body text
serves as documentation. Every other agent in the project lists all its skills in the body
text.
Model: Claude
Assessment: This is likely a genuine finding. The pattern across all other agents in the
project is to list all skills in the agent body text. The asymmetry between opencode.json
(which has both skills) and the agent's own body text (which lists only one) is the same
class of inconsistency as U-W-01. GPT and Gemini may not have flagged it because it has no
functional impact — OpenCode loads skills from config, not from agent body text. However,
for documentation consistency, it should be addressed.
```

---

## Divergence Analysis

```
[D-01] Topic: Severity of stale skill count (U-W-01)
Claude says: Warning — inconsistent with how every other agent's skills are listed
GPT says: Warning — creates a false distinction between the two skills
Gemini says: Suggestion — "technically accurate but stylistically inconsistent"
Assessment: Claude and GPT are correct to rate this as Warning. The inconsistency is not
merely stylistic — it creates a factual mismatch between story-orchestrator.md and both
opencode.json and wiki-maintainer.md. Warning is appropriate.
Resolution: Warning (majority view adopted)
```

```
[D-02] Topic: Severity of 15K/25K budget ambiguity (U-W-02)
Claude says: Suggestion — "could confuse agents or developers reading the skill"
GPT says: Suggestion — "a reader may find the apparent contradiction confusing"
Gemini says: Warning (Correctness) — "could mislead an agent assembling context" to under-allocate
Assessment: Gemini's reasoning is the strongest. This skill is consumed by agents, not
humans reading docs at leisure. An agent parsing "the ~15K token budget for the story
context portion" could reasonably interpret the total story context budget as 15K rather
than 25K, leading to under-allocation and degraded output quality. The functional risk
elevates this beyond a documentation suggestion.
Resolution: Warning (Gemini's view adopted; elevated from majority Suggestion)
```

```
[D-03] Topic: Characterization of test file changes (U-W-03)
Claude says: Warning — correctly identifies four new test methods and docstring change
GPT says: Suggestion — describes as "ruff-reformatted assert statements" (cosmetic)
Gemini says: Warning — correctly identifies new test methods and docstring change
Assessment: Claude and Gemini accurately characterized the changes. GPT's description of
"reformatted assert statements" is factually inaccurate — the diff includes four entirely
new test method declarations, not reformatting of existing code. The 2-vs-1 split strongly
favors Claude and Gemini's characterization.
Resolution: Warning (majority view adopted; GPT's characterization corrected)
```

---

## Recommended Actions (Prioritized)

```
1. [U-W-01] ★★★ Fix: Change "uses one skill:" to "uses two skills:" in
   docs/features/story-orchestrator.md L138 and list both skills as bullet points
   (Warning — all models agree)

2. [U-W-02] ★★★ Fix: Clarify "~15K token budget" in context-budgeting SKILL.md L83
   to explicitly state it is the wiki-page sub-allocation within the ~25K story context
   budget (Warning — all models agree)

3. [U-W-03] ★★★ Fix: Move unrelated test_compaction_plugin.py changes to the
   appropriate branch (issues #23/#68), or document inclusion rationale in commit
   message (Warning — all models agree)

4. [S-W-01] ★☆☆ Fix: Add wiki-conventions to the Skills section of
   .opencode/agents/wiki-maintainer.md body text for consistency (Warning — Claude only)

5. [M-S-01] ★★☆ Consider: Add sync comments to duplicated entity type tables and
   detail level sections across skills (Suggestion — 2/3 models agree)
```
