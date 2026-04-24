---
date: "2026-04-25"
issue: 161
pr: 171
category: agent
targets:
  - ".github/notes/gotchas.md"
  - ".github/agents/_shared/review-checklist.md"
  - ".github/agents/coder.agent.md"
severity: minor
status: active
---

## `_validate_story_name()` required at all Python entry points accepting user-supplied story names

### Finding

PR #171's `run_pipeline()` and `resume_pipeline()` — the two public entry points in
`src/presentation/orchestrator.py` — constructed file paths directly from the `story_name`
parameter without calling `_validate_story_name()` from `src/tools/_io.py`. Every existing
story-facing tool (savepoint_manager, story_state, wiki tools, critique_runner, etc.) calls this
function immediately upon receiving a story name, enforcing two invariants: (1) path traversal
rejection (`../` and similar sequences via `is_relative_to()`), and (2) normalisation of the
story directory name to kebab-case. Omitting this call in the orchestrator entry points created a
new path traversal surface.

Identified as a singular GPT finding (S-I-03 Warning). Not detected by Claude or Gemini. Two of
three models missing this pattern suggests it is not sufficiently prominent in the agent system
instructions.

### Observation

`_validate_story_name()` is the canonical story-name security guard for this project. Its
consistent presence in every existing tool makes any new module that omits it an outlier. However,
the function is not yet called out as a mandatory step in the review checklist or the coder rules
— reviewers encounter it only by noticing its absence through code comparison against other tools.
Given the 2-of-3 miss rate in this review, making the requirement explicit is warranted.

### Suggested Improvement

1. Add a Phase 4 Security bullet to `.github/agents/_shared/review-checklist.md` requiring
   `_validate_story_name()` in new Python entry points that accept a `story_name` parameter.
2. Add a sub-bullet to Coder Rule 9 in `.github/agents/coder.agent.md` naming
   `_validate_story_name()` as the canonical project guard implementation.
3. Add gotcha entry #018 to `.github/notes/gotchas.md` under `## Story Storage` documenting
   the requirement.

### Action Taken

Applied:
- Added gotcha entry #018 (`gotcha-validate-story-name-entry-point-requirement-018`) to
  `.github/notes/gotchas.md` under `## Story Storage`.
- Added a Phase 4 Security bullet to `.github/agents/_shared/review-checklist.md`.
- Added `_validate_story_name()` sub-bullet to Coder Rule 9 in `.github/agents/coder.agent.md`.
