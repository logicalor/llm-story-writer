---
date: "2026-04-25"
issue: 173
pr: 179
category: agent
targets:
  - "prompts/agents/story-orchestrator.md"
severity: minor
status: archived
---

## Tools table uses kebab-case logical names; src/tools/ uses snake_case filenames

### Finding

The `## Tools` table in `story-orchestrator.md` uses kebab-case logical names (e.g., `character-mgr`, `savepoint-mgr`, `setting-mgr`) for tools. The actual Python files in `src/tools/` use snake_case with full words (`character_manager.py`, `savepoint_manager.py`, `setting_manager.py`). The original table header note (`src/tools/<tool_name>.py`) implied a simple substitution, but `character-mgr` → `character_manager.py` requires knowing that `mgr` expands to `manager` — this is not a mechanical transformation.

Flagged by a Gemini singular reviewer during PR #179 review as a pre-existing documentation gap.

### Observation

Readers cannot trivially locate the Python file for a given logical tool name when abbreviated names are used. The gap does not cause runtime failures but hinders debugging and onboarding. A future cleanup pass should either:

1. Update the table to use the exact snake_case filenames matching `src/tools/`, or
2. Add a clear mapping in the table header that lists both the logical name and the corresponding filename.

This is a pre-existing gap introduced before PR #179 and is not a regression.

### Suggested Improvement

File a follow-up GitHub issue to audit the `## Tools` table and replace kebab logical aliases with (or alongside) their exact `src/tools/*.py` filenames. As an interim measure, update the table header note to explicitly state the naming convention.

### Action Taken

Applied (interim): updated the `## Tools` table header in `prompts/agents/story-orchestrator.md` to clarify that names are kebab-case aliases and provide explicit examples of the expansion rule (`savepoint-mgr` → `savepoint_manager.py`, `character-mgr` → `character_manager.py`). Full table normalisation deferred to a follow-up issue.
