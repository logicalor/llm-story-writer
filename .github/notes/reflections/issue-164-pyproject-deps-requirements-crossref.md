---
date: "2026-04-25"
issue: 164
pr: 175
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## `[project.dependencies]` created with only 2 of 7 runtime dependencies

### Finding

PR #175 added a `[project.dependencies]` section to `pyproject.toml` for the first time. The Coder added only 2 packages (`textual` and `openai`) — the two directly referenced in the immediate task scope. The remaining 5 runtime packages already declared in `requirements.txt` were omitted. The review cycle caught this before merge.

### Observation

The Coder added only the packages relevant to the specific feature being implemented, not the complete set of runtime dependencies. This is a natural tendency when the task says "add dependency X to pyproject.toml" — the Coder adds X and stops. But when the `[project.dependencies]` section is being **created from scratch**, its purpose is to be the authoritative packaging declaration for the entire project. A partial migration creates an inconsistent packaging state that fails in clean installs and CI environments that use `pip install -e .` rather than `pip install -r requirements.txt`.

There is no existing rule covering pyproject.toml dependency completeness during section creation.

### Suggested Improvement

Add a sub-bullet to Rule 6 in `coder.agent.md`: when creating a new `[project.dependencies]` section in `pyproject.toml`, cross-reference `requirements.txt` to declare all runtime packages. If the full migration is out of scope, note the partial state explicitly in the handoff summary so the Orchestrator can track it.

### Action Taken

Applied: added "When creating a new `[project.dependencies]` section in `pyproject.toml`" sub-bullet to Rule 6 in `.github/agents/coder.agent.md`.
