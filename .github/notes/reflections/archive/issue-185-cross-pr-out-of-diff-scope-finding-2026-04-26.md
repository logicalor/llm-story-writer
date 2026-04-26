---
date: "2026-04-26"
issue: 185
pr: 198
category: agent
targets:
  - ".github/agents/synthesizing-reviewer.agent.md"
severity: minor
status: archived
---

## Reviewer violation findings for files not in the PR diff are out-of-scope

### Finding

During PR #198, finding S-I-02 (Claude) flagged `consistency_checker.py` as violating gotcha #032 (bare `except Exception:` discarding the error object). The file was not in the PR diff — no changes were made to it in this PR. The violation, if real, predates these changes entirely. The finding was correctly classified as out-of-scope by the Orchestrator.

### Observation

The Synthesizing Reviewer's existing false-positive filters address gitignored paths (security findings), structural existence claims, and annotation artifacts. None of them cover the pattern where a reviewer flags a coding convention violation in a file that was not changed in the current PR. These findings surface genuine technical debt but are categorically out-of-scope for the PR under review — they describe pre-existing issues, not regressions introduced by the current changes.

Without a filter, the Synthesizing Reviewer may surface these as legitimate Singular findings, leaving the Orchestrator to manually determine they are out-of-scope. Adding an explicit filter reduces noise and prevents wasted triage effort.

### Suggested Improvement

**`synthesizing-reviewer.agent.md` Step 2** — add a new false-positive filter immediately after the "Companion file not updated" claims filter:

> **Out-of-diff violation claims filter:** If a finding asserts that a file violates a coding convention, pattern, or gotcha (e.g., "file X uses bare `except Exception:` without capturing the error object") and that file does NOT appear in the PR diff (`git diff --name-only development...HEAD`), the finding is out-of-scope for this PR. The violation, if real, predates these changes and belongs in a separate follow-up issue rather than a fix in this PR. Downgrade to "out-of-scope — file not changed in this PR" and exclude from consensus counts. Do not conflate historical technical debt in unmodified files with defects introduced by this PR. (Source: issue #185, PR #198 — `consistency_checker.py` flagged for gotcha #032 violation but was not in the PR diff.)

### Action Taken

Applied: added "Out-of-diff violation claims filter" to `synthesizing-reviewer.agent.md` Step 2.
