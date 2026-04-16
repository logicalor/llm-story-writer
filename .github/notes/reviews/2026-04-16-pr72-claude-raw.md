# Code Review Report — PR #72

**Branch:** `feat/issue-25-context-budgeting-wiki-skills`
**Reviewer:** Claude
**Date:** 2026-04-16

---

## Review Summary

This PR introduces two new OpenCode skills (`context-budgeting` and `wiki-conventions`) and extends the existing `wiki-maintenance` skill with alias edge cases and the ConStory-Bench error taxonomy. Documentation is updated consistently across `docs/features/story-orchestrator.md` and `docs/features/wiki-maintainer.md`. The main concerns are a stale prose count in the story-orchestrator docs, a missing skill reference in the wiki-maintainer agent definition, and unrelated test changes bundled into the branch.

**Files Reviewed:** 7
**Findings:** 0 Critical, 3 Warning, 2 Suggestion

---

## Findings

### Critical Findings

None.

### Warning Findings

```
[W-01] Stale prose count — wiki-maintainer "uses one skill" should be "uses two skills"
Category: Documentation
Severity: Warning
File: docs/features/story-orchestrator.md
Lines: 138-141
Description: The wiki-maintainer subsection says "The agent uses one skill:" followed by
  wiki-maintenance, then adds "The agent also has access to the **wiki-conventions** skill..."
  as a separate paragraph. This is inconsistent with how every other agent's skills are listed
  in the same file (chapter-writer says "three skills:" with a bullet list, outline-planner
  says "two skills:" with a bullet list). The wiki-maintainer now has two skills in
  opencode.json — the count and format should match. The docs/features/wiki-maintainer.md
  file correctly says "uses two skills:" with both listed, making this file internally
  inconsistent with its own feature doc.
Suggestion: Change "uses one skill:" to "uses two skills:" and move wiki-conventions into the
  bullet list, removing the separate "also has access to" paragraph:

  The agent uses two skills:
  - **wiki-maintenance** — entity extraction rules, confidence taxonomy, ...
  - **wiki-conventions** — page type schemas, frontmatter specifications, and naming conventions
```

```
[W-02] Agent body text does not list wiki-conventions skill
Category: Documentation
Severity: Warning
File: .opencode/agents/wiki-maintainer.md
Lines: 22-23
Description: The wiki-maintainer agent definition lists only wiki-maintenance in its
  "## Skills" section, but opencode.json now declares both wiki-maintenance and
  wiki-conventions in the skills array. While OpenCode loads skills from config automatically,
  the agent body text serves as documentation for the agent's capabilities. Every other agent
  in the project lists all its skills in the body text. The wiki-maintainer should do the same
  to avoid confusion when reading the agent definition directly.
Suggestion: Add wiki-conventions to the Skills section:

  ## Skills
  - **wiki-maintenance** — Entity extraction rules, confidence taxonomy, ...
  - **wiki-conventions** — Page type schemas, YAML frontmatter specs, wikilink conventions, naming rules.
```

```
[W-03] Unrelated test changes bundled into issue-25 branch
Category: Style
Severity: Warning
File: tests/unit/test_compaction_plugin.py
Lines: 1, 72-110
Description: This branch is for issue #25 (context-budgeting and wiki-conventions skills),
  but the test file diff includes a docstring update referencing Issues #23/#68 and four new
  test methods for the compaction plugin (test_plugin_context_interface_defined,
  test_compaction_input_interface_defined, test_compaction_output_interface_defined,
  test_plugin_export_uses_typed_parameters). These test additions are from a different
  feature (compaction plugin type safety) and are unrelated to wiki/context skills. Bundling
  unrelated changes makes the branch harder to review, revert, and bisect.
Suggestion: Move the test changes to their own branch/PR under the relevant issue (#23 or
  #68), or acknowledge the inclusion in the commit message with a clear rationale.
```

### Suggestions

```
[S-01] Duplicated entity type table across two skills
Category: Documentation
Severity: Suggestion
File: .opencode/skills/wiki-conventions/SKILL.md
Lines: 42-56
Description: The 12-row entity type table with frontmatter fields appears identically in both
  wiki-conventions/SKILL.md and wiki-maintenance/SKILL.md. Similarly, the detail level
  guidelines (L1/L2/L3 definitions and token targets) appear in all three skills
  (context-budgeting, wiki-conventions, wiki-maintenance). These are deliberately self-contained
  for agents that load only a subset of skills, which is a valid design choice. However, any
  future change to entity types or detail levels must be synchronised across all three files —
  this is a maintenance risk.
Suggestion: Consider adding a comment at the top of duplicated sections noting the canonical
  source and which files must be kept in sync, e.g.:
  <!-- Canonical: wiki-conventions/SKILL.md. Keep in sync with wiki-maintenance/SKILL.md -->
```

```
[S-02] Context-budgeting skill references 15K token budget for "story context portion"
  but ADR 002 allocates 25K
Category: Documentation
Severity: Suggestion
File: .opencode/skills/context-budgeting/SKILL.md
Lines: 82
Description: The detail level selection section says "Pages are sorted by relevance score and
  assigned detail levels top-down within the ~15K token budget for the story context portion
  of the window." However, the token budget table at the top of the same file allocates ~25K
  tokens for "Story context (loaded by tool)". The 15K figure may refer to the wiki entity
  subset of the 25K story context budget (with the remainder going to chapter outline, recap,
  etc.), but this is not explicitly stated and could confuse agents or developers reading the
  skill.
Suggestion: Clarify the relationship between the 25K total story context budget and the ~15K
  entity budget by adding a brief note, e.g.: "~15K of the 25K story context budget is
  allocated to wiki entity pages; the remainder covers the chapter outline and recap."
```

---

## Overall Assessment

The PR is well-structured and delivers meaningful skill documentation for the wiki and context management subsystems. The new skill files are thorough, internally consistent, and well-aligned with the referenced ADRs. The wiki-maintenance extensions (alias edge cases, ConStory-Bench taxonomy) are clean additions that don't disrupt existing content.

The two warning-level documentation issues (W-01, W-02) should be fixed before merge — they create inconsistencies between the agent config, agent body text, and feature documentation that will mislead future readers. W-03 (unrelated test changes) is a process concern that should be addressed by either splitting the changes or documenting the inclusion.

No security, correctness, or performance concerns. The code is ready for merge after addressing the two documentation warnings.
