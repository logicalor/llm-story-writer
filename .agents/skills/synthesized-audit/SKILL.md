---
name: synthesized-audit
description: Use when running a repository healthcheck, compliance audit, readiness audit, or Copilot-style synthesized audit. Replaces Copilot's multi-model Synthesizing Auditor with sequential persona audits and consensus synthesis.
---

# Synthesized Audit

This is the Codex-native counterpart to `.github/agents/synthesizing-auditor.agent.md`.
Codex does not fan out to Claude, GPT, and Gemini models, so this skill uses
separate audit personas over one shared evidence bundle, then synthesizes their
findings with consensus weighting.

Use this for broad repository audits. For PR or local-change review, use
`code-review` instead.

## Ground Rules

- Load `project-memory` first and query the `audits`, `conventions`, and
  `reflections` collections for relevant prior findings.
- Write only `.github/notes/` audit or reflection files unless the user
  explicitly asks for fixes.
- Do not create GitHub issues automatically. Ask before filing or handing off
  findings.
- Prefer current local files over older Copilot instructions when they conflict.
- Treat `.github/agents/` as reference material for Copilot, not as callable
  Codex tooling.
- Use one shared evidence bundle for all persona passes so differences come from
  perspective, not from inconsistent inputs.

## Audit Personas

Run the same evidence through these personas sequentially:

| Persona | Focus |
| --- | --- |
| Architect | Clean architecture boundaries, ADR alignment, module direction, workflow shape, stale design assumptions |
| Maintainer | Tests, lint/type health, dependency drift, implementation quality, operational risk, repository hygiene |
| Product Documenter | Planning alignment, README/docs accuracy, agent/skill instruction drift, user-facing gaps, deferred work |

Each persona should produce an independent raw report. Keep raw reports concise
but structured enough to cross-reference.

## Workflow

1. Establish scope:
   - Confirm whether the audit is full-repo, release readiness, workflow/agent
     system, docs, architecture, tests, or a named feature.
   - If the user did not specify, default to full-repo healthcheck.
2. Build the "should" state:
   - Read `AGENTS.md`, `.github/notes/README.md`, relevant `.github/notes/*`,
     current ADRs under `docs/planning/adr/`, active planning docs under
     `docs/planning/`, and relevant skill files under `.agents/skills/`.
   - Include Copilot audit references only as background:
     `.github/agents/_shared/audit-process.md`,
     `.github/agents/_shared/multi-model-synthesis.md`, and
     `.github/agents/synthesizing-auditor.agent.md`.
3. Build the "is" state:
   - Inspect `git status --short`, recent `git log --oneline -50`, changed or
     stale branches when relevant, and open work if GitHub context is available.
   - Inspect source, tests, docs, skills, prompts, and configuration relevant to
     the audit scope.
4. Verify mechanically where useful:
   - Run the repo's validation commands when the audit scope warrants it:
     `ruff check .`, `ruff format --check .`, `mypy src/`, and relevant
     `pytest` commands.
   - Record command results exactly enough that a future reader can distinguish
     current failures from inferred risk.
5. Run persona passes:
   - Architect report: architecture and plan compliance.
   - Maintainer report: code/test/build/security/repo hygiene.
   - Product Documenter report: docs/planning/instruction/user workflow drift.
6. Cross-reference findings:
   - Match by substance, not wording.
   - Classify findings as unanimous, majority, or singular across the three
     personas.
   - Verify any high-impact finding against files before including it.
7. Synthesize:
   - Produce the final synthesized audit report using the format below.
   - If requested, write it to
     `.github/notes/audits/YYYY-MM-DD-synthesis.md`.
   - Add one ChromaDB `audits` document per key finding when the Chroma tools are
     available.

## Consensus Levels

| Consensus | Meaning | Confidence |
| --- | --- | --- |
| Unanimous | All three personas identify the same issue | High, ★★★ |
| Majority | Two personas identify the same issue | Medium, ★★☆ |
| Singular | One persona identifies the issue | Lower, ★☆☆ |

Singular findings are still valuable. Include them when they are evidence-backed
or reveal a plausible blind spot, but label the confidence honestly.

## Output Format

### Synthesis Overview

Summarize overall health, agreement between personas, and the highest-confidence
findings.

`Persona Agreement Score: X/10` where 10 means the reports aligned closely.

### Individual Report Summaries

| Persona | Overall Assessment | Unique Focus Areas | Critical Count | Warning Count |
| --- | --- | --- | --- | --- |
| Architect | ... | ... | N | N |
| Maintainer | ... | ... | N | N |
| Product Documenter | ... | ... | N | N |

### Development Stage

Use this when the audit compares the repo to planning docs.

| Phase | Status | Completion | Agreement |
| --- | --- | --- | --- |
| Phase name | Done / In Progress / Not Started | X/Y tasks | Unanimous / Majority / Split |

### Consensus Findings

Group findings by consensus level, then severity:

```text
[U-C-01] Title
Severity: Critical | Warning | Info
Category: Architecture | Code Quality | Tests | Build | Security | Documentation | Planning | Workflow
Detail: Synthesized description with file evidence.
Personas: Architect yes | Maintainer yes | Product Documenter yes
Impact: Why this matters.
Suggested action: Concrete next step.
```

For majority findings, include `Dissenting view:`. For singular findings,
include `Assessment:` explaining why the finding may be genuine or lower
confidence.

### Divergence Analysis

Document important disagreements:

```text
[D-01] Topic
Architect says: ...
Maintainer says: ...
Product Documenter says: ...
Assessment: Which reading is most likely correct and why.
Resolution: How the final findings treat it.
```

### Deviations From Plan

Include deviations that at least two personas identify or that have direct file
evidence.

### Risk Assessment

Combine technical, process, dependency, documentation, and workflow risks.

### Recommended Actions

Prioritize unanimous criticals, then majority criticals, warnings, and singular
follow-ups.

## Audit Note Template

When writing the synthesis to `.github/notes/audits/`, use:

```markdown
## Synthesized Audit — YYYY-MM-DD

**Audit Type:** Codex persona synthesis
**Personas:** Architect + Maintainer + Product Documenter
**Persona Agreement Score:** X/10
**Overall Health:** Healthy | Needs Attention | At Risk
**Development Stage:** Phase X — Y% complete

### Finding Counts by Consensus

| Consensus | Critical | Warning | Info |
| --- | --- | --- | --- |
| ★★★ Unanimous | N | N | N |
| ★★☆ Majority | N | N | N |
| ★☆☆ Singular | N | N | N |

### Key Findings

- [U-C-01] Brief summary (★★★)
- [M-W-01] Brief summary (★★☆)

### Divergences

- [D-01] Brief summary and resolution

### Actions Taken

- Issues created: none unless explicitly requested
- Notes updated: `.github/notes/audits/YYYY-MM-DD-synthesis.md`
- ChromaDB: finding IDs added to `audits`, or unavailable
```
