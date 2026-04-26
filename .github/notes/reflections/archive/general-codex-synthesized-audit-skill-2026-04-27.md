---
date: "2026-04-27"
issue: general
pr: none
category: skill
targets:
  - ".agents/skills/synthesized-audit/SKILL.md"
  - ".agents/skills/github-workflow/SKILL.md"
  - "AGENTS.md"
severity: major
status: archived
---

## Codex Synthesized Audit Skill

### Finding

The Copilot agent system has `.github/agents/synthesizing-auditor.agent.md`,
which coordinates three model-specific auditors and writes consensus audit
reports. The Codex workflow skills did not have an equivalent; `code-review`
covered PR/local-change review and synthesis of existing reports, but not a
full repository healthcheck against planning docs, ADRs, tests, documentation,
and workflow instructions.

### Observation

Codex cannot rely on the same three-model fanout pattern. The closest equivalent
is to run multiple independent perspectives over one shared evidence bundle and
then synthesize the results with explicit consensus levels. This preserves the
useful part of the Copilot auditor: disagreement analysis, confidence weighting,
and durable audit notes.

### Suggested Improvement

Create a `.agents/skills/synthesized-audit/SKILL.md` skill with sequential
Architect, Maintainer, and Product Documenter persona passes. Add it to the
Codex workflow skill list in `AGENTS.md` and map the Copilot Auditor /
Synthesizing Auditor touchpoint in `.agents/skills/github-workflow/SKILL.md`.

### Action Taken

Applied: added the `synthesized-audit` skill, listed it in `AGENTS.md`, and
mapped the Copilot audit touchpoint to the new skill in `github-workflow`.
