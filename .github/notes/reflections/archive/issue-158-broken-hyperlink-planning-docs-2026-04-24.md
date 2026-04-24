---
date: "2026-04-24"
issue: 158
pr: 167
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## Planning docs committed with broken hyperlinks to non-existent targets

### Finding

`docs/planning/python-native-migration/prd.md` referenced `[ADR 007](./adr/007-python-native-orchestration.md)` in two places (lines 8 and 165). `docs/planning/adr/007-python-native-orchestration.md` does not exist in the repository. The link was dead at commit time. Surfaced by Gemini during the synthesized review; confirmed by file search.

### Observation

The PRD was written as part of PR #167's documentation scope. The intent appears to have been that creating the ADR was part of the task, but it was not included in the commit. No existing rule requires the Coder to verify that internal hyperlinks in newly-written or updated documents resolve to actual files before committing. A dead link in a planning doc is a low-severity defect on its own, but planning docs are cited by agents and future contributors — a `[ADR 007](./adr/007...)` link that 404s silently erodes trust in the documentation corpus.

The fix (either create the ADR or replace the hyperlink with plain text like `ADR 007 (to be created)`) is small, but requires a rule to prompt it.

### Suggested Improvement

Add a sub-bullet to Rule 7 in `coder.agent.md` requiring hyperlink verification in any doc created or substantially edited as part of the task: verify each `[text](path)` link target exists, or replace with plain text marked `(to be created)`.

### Action Taken

Applied: added sub-bullet to Rule 7 in `.github/agents/coder.agent.md` covering hyperlink target verification before returning to the Orchestrator.
