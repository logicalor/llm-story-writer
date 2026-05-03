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
verify the file reference before committing it to the issue body.

The planning-workflow SKILL.md already included "Verify every path and link included in a plan"
as a guardrail, but this was scoped to hyperlinks. File references in prose are not hyperlinks
and would not be caught by a link-check. A targeted clarification closes the gap.

### Suggested Improvement

Extend the "Verify every path and link" guardrail in the planning-workflow SKILL.md to explicitly
cover prose function and file references with specific grep commands.

### Action Taken

Applied: replaced "Verify every path and link included in a plan" with a detailed guardrail
covering Markdown hyperlinks, prose file references (ls check), and function/class references
(grep check). (Source: issue #320 — issue body referenced `src/tools/wiki_bootstrap.py` but
`bootstrap_wiki_from_story` lives in `src/tools/wiki_extract.py`.)
