# Code Review Report — PR #72

**Branch:** `feat/issue-25-context-budgeting-wiki-skills`
**Reviewer:** Gemini
**Date:** 2026-04-16

---

## Review Summary

This PR adds two new OpenCode skills (`context-budgeting` and `wiki-conventions`) and augments the existing `wiki-maintenance` skill with alias edge cases and a ConStory-Bench error taxonomy. The skill content faithfully reproduces the authoritative ADR source material, the `opencode.json` registration is correct, and documentation is updated consistently. Two issues of note: an internal token budget inconsistency in the context-budgeting skill, and unrelated test changes bundled into the branch.

**Files Reviewed:** 7
**Findings:** 0 Critical, 2 Warning, 2 Suggestion

---

## Findings

### Warning Findings

```
[W-01] Unrelated test changes included in branch
Category: Style
Severity: Warning
File: tests/unit/test_compaction_plugin.py
Lines: 1, 72-110
Description: The review package described these changes as "pre-existing ruff format changes only
(whitespace reformatting of assert statements)" but the actual diff shows substantive additions:
the docstring was changed from "Verification tests for Issue #23 — Build Compaction Plugin" to
"Verification tests for compaction plugin (Issues #23, #68)", and four new test methods were added
(test_plugin_context_interface_defined, test_compaction_input_interface_defined,
test_compaction_output_interface_defined, test_plugin_export_uses_typed_parameters). These test
compaction plugin interfaces related to issues #23/#68 and are unrelated to issue #25
(context-budgeting and wiki-conventions skills). Bundling unrelated changes makes the branch
harder to review and the git history harder to bisect.
Suggestion: Move the test_compaction_plugin.py changes to the appropriate branch
(feat/issue-23-compaction-plugin or a dedicated #68 branch) and rebase this branch to exclude them.
```

```
[W-02] Internal token budget inconsistency between table and Stage 2
Category: Correctness
Severity: Warning
File: .opencode/skills/context-budgeting/SKILL.md
Lines: 22-28, 83
Description: The token budget table (line 22-28) allocates ~25,000 tokens to "Story context
(loaded by tool)" with the note "Chapter outline + relevant sheets + recap". However, Stage 2
(line 83) states: "Pages are sorted by relevance score and assigned detail levels top-down within
the ~15K token budget for the story context portion of the window." The phrase "for the story
context portion" reads as if the entire story context budget is 15K, contradicting the 25K in the
table. In reality, the ~15K (from ADR 005) is the wiki-page allocation within the larger ~25K
story context budget — the remaining ~10K covers the chapter outline and recap. The current
wording creates ambiguity that could mislead an agent assembling context.
Suggestion: Clarify the line to: "Pages are sorted by relevance score and assigned detail levels
top-down within the ~15K wiki-page allocation of the ~25K story context budget." This preserves
the ADR 005 figure while disambiguating from the budget table.
```

### Suggestions

```
[S-01] Stale skill count for wiki-maintainer in story-orchestrator
Category: Documentation
Severity: Suggestion
File: docs/features/story-orchestrator.md
Lines: 138-141
Description: The wiki-maintainer subsection says "The agent uses one skill:" and then separately
adds "The agent also has access to the wiki-conventions skill..." This is technically accurate but
stylistically inconsistent with the chapter-writer subsection (which uses "The agent uses three
skills:" with a unified bullet list) and the outline-planner subsection (which uses "The agent
uses two skills:" likewise). In opencode.json, both wiki-maintenance and wiki-conventions are
registered in the skills array at the same level — neither is secondary.
Suggestion: Rewrite to match the pattern used for other subagents:
  "The agent uses two skills:
  - **wiki-maintenance** — entity extraction rules, confidence taxonomy, structured output
    formats, detail level guidelines, and chapter boundary procedures
  - **wiki-conventions** — page type schemas, YAML frontmatter specifications, wikilink
    conventions, and slug naming rules"
```

```
[S-02] Entity type table duplicated across wiki-conventions and wiki-maintenance
Category: Documentation
Severity: Suggestion
File: .opencode/skills/wiki-conventions/SKILL.md
Lines: 45-62
Description: The 12-row entity type table appears in both wiki-conventions/SKILL.md (lines 45-62)
and wiki-maintenance/SKILL.md (lines 12-29). The tables are identical in structure and content.
This duplication means any future schema change must be applied in two places, risking drift.
Suggestion: Consider having one skill reference the other (e.g., "See the wiki-maintenance skill
for the full entity type table") or extract the table to a shared location. Not urgent — the two
skills serve different audiences — but worth tracking for future refactoring.
```

---

## Verification Summary

| Check | Result |
|-------|--------|
| Token budget table matches ADR 002 | ✅ All six rows identical |
| Scoring formula matches ADR 005 | ✅ Weights 0.40/0.20/0.20/0.10/0.10, threshold 0.15 |
| Retrieval tiers (T1-T4) match ADR 005 | ✅ Methods, priorities, and signals match |
| Detail levels (L1/L2/L3) match ADR 005 | ✅ Token targets and use cases match |
| Priority tiers match ADR 005 | ✅ Protected/High/Medium/Low tiers and demotion rules |
| Delta caching strategy matches ADR 005 | ✅ All 6 steps + target cache hit rate |
| Wiki-maintenance changes additive only | ✅ Two new sections inserted; no existing content altered |
| Batch payload format preserved | ✅ creates/updates/timeline_events with snake_case keys |
| opencode.json valid JSON | ✅ Validated via `json.load()` |
| All referenced skill directories exist | ✅ All 7 skills in opencode.json resolve to SKILL.md files |
| Commit messages follow convention | ✅ `feat(skills):` and `docs:` with issue reference |
| Branch name follows convention | ✅ `feat/issue-25-*` |
| No numbered step list gaps | ✅ Concrete rules 1-5, delta caching 1-6, extraction rules 1-6 |

---

## Overall Assessment

The core deliverables — the two new skills and the wiki-maintenance additions — are well-structured, internally consistent, and faithfully encode the authoritative ADR material. Documentation updates to `story-orchestrator.md` and `wiki-maintainer.md` are thorough and accurately reflect the new skill registrations in `opencode.json`. The only substantive concern is W-02 (the 15K/25K ambiguity in context-budgeting), which could cause an agent to under-allocate story context if it takes the 15K figure as the full budget. The unrelated test changes (W-01) should ideally be moved to the correct branch before merge. With W-02 clarified, the code is ready for merge.
