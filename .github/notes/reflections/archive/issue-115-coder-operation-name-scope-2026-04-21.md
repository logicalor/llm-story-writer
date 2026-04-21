---
date: "2026-04-21"
issue: 115
pr: 116
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## Rule 10 "editing existing" wording excludes new-content writes — operation names still missed

### Finding

During PR #116 (feat/issue-115-fix-audit-warnings), the Coder wrote `operation: load` in the character-mgr and setting-mgr fallback path when the correct value is `operation: load-sheet`. Rule 10 was applied to issue #113 to address this defect class, but it uses the phrase **"When editing existing agent or skill files"**. The Coder was writing new content (a fallback path section), not editing existing documentation — the wording gave an implicit escape hatch. The rule did not fire.

### Observation

The "editing existing" qualifier restricts Rule 10's source-verification requirement to modification of previously-written content. New sections, new flow paths, and new skill examples added during implementation are equally likely to contain fabricated operation names but fall outside the rule's stated trigger condition. The defect class (Coder writes tool operation names without verifying against the Python `OPERATION_MAP` or equivalent dispatch) has now recurred across issues #19, #22, #113, and #115 — four occurrences in four months. Rule 10 must apply unconditionally to any agent or skill content that includes tool call syntax, regardless of whether the file pre-existed.

### Suggested Improvement

In `.github/agents/coder.agent.md`, Rule 10, change:

> **When editing existing agent or skill files** that reference tool operation names, parameter types, or return formats — verify each against the actual Python source …

To:

> **When writing or editing any agent or skill content** that includes tool operation names, parameter types, or return formats — verify each against the actual Python source …

Remove the phrase "Do not assume existing documentation is current." — it is now redundant since the rule applies to both new and pre-existing content.

### Action Taken

Applied: Changed Rule 10 trigger from "When editing existing agent or skill files" to "When writing or editing any agent or skill content", making verification mandatory for new content as well as edits. Removed the now-redundant "Do not assume existing documentation is current." sentence.
