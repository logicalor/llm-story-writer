---
date: "2026-04-30"
issue: 263
pr: 271
category: instruction
targets:
  - ".github/agents/_shared/review-checklist.md"
severity: major
status: active
---

## Retired TypeScript Wrapper Concepts Still Present in Review Checklist

### Finding

The `review-checklist.md` (used by all three reviewer models) still contains multiple references to TypeScript wrappers, Zod schemas, and `.opencode/tools/*.ts` verification steps. These concepts were retired by ADR 007 (Python-native migration) but remain in the shared review protocol.

### Observation

Specific stale references found:
1. Line 21 (General / API signature changes): "Also applies to TypeScript tool wrapper Zod schema changes" — instructs reviewers to grep `.opencode/tools/*.ts` and verify Zod field transitions.
2. Line 46 (Agent Instructions / Tool call contracts): Instructs reviewers to verify parameter key names match "Zod field names in the TS wrapper (`.opencode/tools/*.ts`)" and mentions `.optional()` in Zod schemas.
3. Line 49 (Agent call site parameter casing): Requires matching "camelCase Zod field declarations in the TS wrapper".
4. Line 127 (Phase 7 / Zod `.describe()` text): Instructs verifying Zod `.describe()` strings in `.opencode/tools/*.ts`.

These instructions are now phantom guidance — they direct reviewers to verify against non-existent files and schemas. If reviewers follow these steps literally, they will waste tokens on Zod verification or falsely flag Python-native parameter naming.

### Suggested Improvement

Replace all TypeScript/Zod references in `review-checklist.md` with Python-native equivalents:
- "Zod field names in the TS wrapper" → "argument names in the Python tool (read `argparse.add_argument` declarations in `src/tools/*.py`)"
- `.opencode/tools/*.ts` references → `src/tools/*.py`
- `.optional()` in Zod → conditional argparse validation in Python
- Remove Zod `.describe()` checks entirely; replace with Python docstring/`help=` text verification.

### Action Taken

Proposed for approval: This is a structural change to the shared review checklist used by all reviewer agents. Requires human review before applying to ensure the replacement language is accurate for Python-native tools.
