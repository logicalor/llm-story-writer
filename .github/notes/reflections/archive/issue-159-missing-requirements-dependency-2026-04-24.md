---
date: "2026-04-24"
issue: 159
pr: 168
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## New third-party import added without updating requirements.txt

### Finding

PR #168 introduced `import openai` inside `openai_async_provider.py` without adding `openai` to `requirements.txt`. The package was available in the development environment, so the omission was invisible locally. In a clean installation or CI environment without `openai` pre-installed, the module would raise `ModuleNotFoundError` on first import with no indication that a `requirements.txt` entry was missing.

### Observation

The Coder's Rule 7 already addresses import-level concerns (removing unused imports, placement of inline imports), but none of its sub-bullets cover the package-level validity check: verifying that a newly imported third-party library is also declared as a project dependency. The package availability check and the requirements declaration check are distinct — the first is caught by the Python runtime; the second only surfaces in clean environments.

New infrastructure providers are a natural insertion point for new third-party dependencies (the OpenAI SDK, Claude SDK, Cohere SDK, etc.). Without a rule, each new provider implementation carries the same omission risk.

### Suggested Improvement

Add a sub-bullet to Coder Rule 7 covering third-party import additions: when adding a new import of a package not in the standard library, verify the package appears in `requirements.txt`.

### Action Taken

Applied: added sub-bullet to Rule 7 in `.github/agents/coder.agent.md` after the "inline (function-body) imports" sub-bullet and before "When relocating files".
