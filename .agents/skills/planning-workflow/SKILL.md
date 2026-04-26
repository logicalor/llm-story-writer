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
- Verify every path and link included in a plan.
- Explicitly call out stale Copilot/OpenCode assumptions when a plan touches agent infrastructure.
