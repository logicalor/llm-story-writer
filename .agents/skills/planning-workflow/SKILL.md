---
name: planning-workflow
description: Use when turning a feature idea, vague request, architecture change, or planning document task into a concrete PRD, ADR, task breakdown, or implementation plan for this repository.
---

# Planning Workflow

Plan before implementation when the user asks for planning, the scope is unclear, or the change spans architecture, workflow, or multiple modules.

## Process

1. Load `project-memory`.
2. Clarify the problem, users, success criteria, non-goals, dependencies, and risks.
3. Research the current codebase with `rg`, file reads, and focused Chroma queries.
4. Check GitHub issues and prior planning docs when relevant.
5. Produce a concrete plan with affected files, tests, docs, and validation commands.
6. Record durable discoveries in `.github/notes/` if they will matter later.

## Planning Artifacts

Use `docs/planning/<slug>/prd.md` for product requirements.
Use `docs/planning/<slug>/tasks.md` for task breakdowns.
Use `docs/planning/adr/NNN-<slug>.md` for architecture decisions.

Templates live in `references/templates.md`.

## Guardrails

- Do not write production code while acting only as planner.
- Prefer existing repo patterns over new abstractions.
- Separate "must ship now" from follow-up ideas.
- **Verify every path, link, and named function/class referenced in a plan.** For Markdown hyperlinks: confirm the target file exists. For prose file references (e.g., "the key file is `src/tools/foo.py`"): run `ls src/tools/foo.py` to confirm existence. For function or class references: run `grep -r "def function_name\|class ClassName" src/` to confirm the actual file location. A mismatched filename wastes Researcher cycles and can misdirect the Coder. (Source: issue #320 — issue body referenced `src/tools/wiki_bootstrap.py` but `bootstrap_wiki_from_story` lives in `src/tools/wiki_extract.py`.)
- Explicitly call out stale Copilot/OpenCode assumptions when a plan touches agent infrastructure.
