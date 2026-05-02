---
date: "2026-05-02"
issue: 300
pr: 312
category: instruction
targets:
  - "src/presentation/agents/outline_critic.py"
  - ".github/agents/_shared/review-checklist.md"
severity: minor
---

## OUTLINE_CRITIC_TYPES defined independently in two modules

### Finding

`OUTLINE_CRITIC_TYPES` is defined identically in both `src/presentation/agents/outline_critic.py` and `src/tools/critique_runner.py`. The CLI tool cannot cleanly import from the presentation layer (module-path difference, global sys.path side-effects at import time), so the duplication is an intentional architectural constraint. However, no cross-reference comment exists — a developer adding a new critic prompt file would update one list and not know to update the other.

### Observation

The six critic types (`audiobook-producer`, `book-club-moderator`, `commercial-fiction-editor`, `literary-fiction-reviewer`, `publishing-acquisitions-editor`, `subject-expert`) are the authoritative set controlling which prompt files in `prompts/outline_review/` are exercised. Silent drift between the two lists would cause `OutlineCriticAgent` (Python orchestrator path) and `critique-runner` (LLM orchestrator path) to evaluate different critic sets with no error or warning. There is no automated check that the two lists are equal.

### Suggested Improvement

1. Add a `# Keep in sync with src/tools/critique_runner.py::OUTLINE_CRITIC_TYPES` comment to `outline_critic.py`.
2. Add a `# Keep in sync with src/presentation/agents/outline_critic.py::OUTLINE_CRITIC_TYPES` comment to `critique_runner.py`.
3. Add a review checklist item under the Agent Instructions section: when a PR adds, renames, or removes an `outline_review/` prompt file, verify `OUTLINE_CRITIC_TYPES` is updated in both `src/presentation/agents/outline_critic.py` and `src/tools/critique_runner.py`.

### Action Taken

Applied:
- Added sync cross-reference comment to `OUTLINE_CRITIC_TYPES` in `src/presentation/agents/outline_critic.py`.
- Added sync cross-reference comment to `OUTLINE_CRITIC_TYPES` in `src/tools/critique_runner.py`.
- Added dual critic-type list parity checklist item to `.github/agents/_shared/review-checklist.md` Agent Instructions section.
- Embedded in `reflections` ChromaDB collection.
