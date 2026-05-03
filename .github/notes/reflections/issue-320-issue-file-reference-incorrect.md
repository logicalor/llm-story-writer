<!-- STALE — archived to archive/issue-320-issue-file-reference-incorrect-2026-05-03.md — delete this file -->
---
date: "2026-05-03"
issue: 320
pr: 332
category: skill
targets:
  - ".agents/skills/planning-workflow/SKILL.md"
severity: minor
---

## Issue body referenced wrong filename — function lived in a different tool module

### Finding

The issue for PR #332 (issue #320) referenced `src/tools/wiki_bootstrap.py` as the key file
containing `bootstrap_wiki_from_story`. The function actually lives in `src/tools/wiki_extract.py`.
No file named `wiki_bootstrap.py` exists in the repository. The Researcher correctly identified
this discrepancy during the research phase and reported the actual location, so it did not block
the implementation.

### Observation

When an issue body names a specific source file or function as the implementation target, and that
file does not exist at the stated path, the Researcher and Coder both need to spend cycles
re-discovering the actual location. The Researcher handled this gracefully here, but the pattern
is avoidable: the Planner or issue author can grep for the function name at planning time to
verify the file reference before committing it to the issue body. A one-second grep at plan
creation prevents a multi-minute re-research pass later.

The planning-workflow SKILL.md already includes "Verify every path and link included in a plan"
as a guardrail, but this is scoped to hyperlinks. File references in prose (e.g., "the key file
is `src/tools/wiki_bootstrap.py`") are not hyperlinks and would not be caught by a link-check.
A targeted clarification to also verify function/class locations would close the gap.

### Suggested Improvement

Extend the "Verify every path and link included in a plan" guardrail in the planning-workflow
SKILL.md to explicitly cover function and file references in prose, not only Markdown hyperlinks:

> **Verify every path, link, and named function/class referenced in a plan.** For hyperlinks:
> confirm the target file exists. For prose file references (e.g., "the key file is
> `src/tools/foo.py`"): run `ls src/tools/foo.py` to confirm existence. For function/class
> references: run `grep -r "def function_name\|class ClassName" src/` to confirm the actual
> location. A mismatched filename wastes Researcher cycles and can misdirect the Coder.
> (Source: issue #320 — issue body referenced `src/tools/wiki_bootstrap.py` but
> `bootstrap_wiki_from_story` lives in `src/tools/wiki_extract.py`.)

### Action Taken

Applied: updated "Verify every path and link included in a plan" guardrail in
`.agents/skills/planning-workflow/SKILL.md` to cover prose file references and function locations.
