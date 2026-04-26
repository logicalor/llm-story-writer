---
name: code-review
description: Use when reviewing local changes, PRs, review reports, or synthesized multi-model findings. Prioritizes bugs, regressions, missing tests, security issues, and stale agent/skill instructions.
---

# Code Review

Review like a maintainer. Findings first, ordered by severity, with file and line references. Summaries come after findings.

## Review Sources

1. Inspect `git status --short` and changed files.
2. Compare against `development` when reviewing a branch.
3. Load `project-memory` and query `conventions` for relevant gotchas.
4. Read the implementation and tests, not only the diff, when behavior depends on surrounding code.
5. For PR review, fetch existing PR context if available.

## What To Prioritize

- correctness regressions
- security and path traversal risks
- boundary validation gaps
- data loss or corrupt-state paths
- missing or weak tests for changed behavior
- stale docs, agent instructions, skill files, and workflow references
- mismatches between CLI flags, tool schemas, and Python implementation

## Local Review Checklist

Read `references/checklist.md` for the detailed repo checklist. Use it especially when reviewing agent/skill files or tool interfaces.

## Synthesis

If given multiple raw review reports:

1. Normalize duplicate findings.
2. Verify claims against the current files.
3. Classify as unanimous, majority, or singular.
4. Downgrade unverified structural claims.
5. Exclude out-of-diff issues from required fixes unless they block the changed behavior.

Write synthesized reports to `.github/notes/reviews/YYYY-MM-DD-prN-synthesis.md` when requested.
