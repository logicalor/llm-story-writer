---
date: "2026-04-23"
issue: 144
pr: 145
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## snake_case vs camelCase parameter mismatch in agent tool call instructions

### Finding

PR #145 introduced a new `wiki-extract` tool. The Mode 2 step body in `.opencode/agents/wiki-maintainer.md` instructed the agent to call `wiki-extract` with `chapter_number` and `chapter_text_path` (snake_case), but the TypeScript Zod schema in `.opencode/tools/wiki-extract.ts` declares `chapterNumber` and `chapterTextPath` (camelCase). All three reviewers (Claude, GPT, Gemini) flagged this unanimously as a Critical blocker: OpenCode silently drops unknown keys, so the Zod runtime guard would have returned `Error: chapterNumber is required for update-from-chapter` and made the entire Phase 7c workflow non-functional.

### Observation

This is the fifth occurrence of the broader "agent call site does not match Zod schema" defect class (issues #19, #22, #113, #133, now #144) — and it happened despite Coder Rule 10(d) already requiring parameter-key verification against the TS wrapper. The recurrence pattern is informative:

- Rule 10(d)'s example contrasts **different words** (`step:` vs `savepoint:`).
- Issue #22's `dual-naming-convention` note contrasts **camelCase direct params vs snake_case batch-payload JSON keys** — i.e. two intentionally different conventions inside a single tool surface.
- This new defect is **the same word in different cases** across the agent-file / Zod boundary (`chapter_number` ↔ `chapterNumber`).

The Coder, when authoring step body prose, has at least three competing conventions to choose from (Python CLI flags, Zod field names, batch JSON keys), all carrying the same semantic name. Without an explicit callout that **agent-file step text must use the camelCase Zod field names verbatim**, the path of least resistance is to mirror the snake_case Python flag the author just wrote.

### Suggested Improvement

Strengthen Coder Rule 10(d) with an explicit case-sensitivity sub-example covering the same-word/different-case case, and cross-reference issue #22's distinction between direct-call params (camelCase) and batch-payload JSON (snake_case).

### Action Taken

Applied: added camelCase case-sensitivity sub-example to Coder Rule 10(d) in `.github/agents/coder.agent.md` referencing PR #145 and contrasting with the issue #22 batch-payload convention. Also added "Agent call site parameter casing matches Zod schema exactly" item to `.github/agents/_shared/review-checklist.md` Phase 2 Agent Instructions.
