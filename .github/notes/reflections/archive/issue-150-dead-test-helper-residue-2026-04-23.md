---
date: "2026-04-23"
issue: 150
pr: 151
category: agent
targets:
  - ".github/agents/test-writer.agent.md"
severity: minor
status: archived
---

## Dead test helper (`_run_main` / `FailedToRaise`) persisted in test module

### Finding

The `wiki-extract` test module contained a `_run_main` helper and a `FailedToRaise` exception class that were dead code — no test invoked them, and `FailedToRaise` had a syntax/semantic defect that would prevent use. New tests correctly used the canonical `_invoke_main` pattern, so functionality was unaffected, but the Claude reviewer flagged the orphaned scaffolding. Pre-existing before this PR; the fix removed it during review follow-up.

### Observation

When a test file grows by accretion across multiple PRs, broken or abandoned helpers can accumulate and invite copycat use by future contributors. The Test Writer agent correctly ignored the dead helper this cycle, but a less careful future iteration could easily pattern-match against it. Low-probability but cheap to prevent.

Scope tension: cleaning unrelated pre-existing dead code during a feature PR risks scope inflation (see issue #111 coder-scope-creep). The right bar is narrow — if a dead helper sits adjacent to the tests being added **and** resembles a template that could be copied, the Test Writer should note it and the Reviewer should flag it for removal. Broader dead-code sweeps remain out of scope.

### Suggested Improvement

Add a short bullet to the Test Writer's "Research Before Writing" section advising that when extending an existing test file, any pre-existing helper whose body is clearly broken (undefined names, unreachable branches, obviously unused) should be flagged in the verification report rather than emulated. This keeps the fix out of the PR's direct scope but surfaces the issue for reviewer follow-up.

### Action Taken

Applied minor addition to `.github/agents/test-writer.agent.md` under "Research Before Writing" — new bullet instructing the Test Writer to flag (not silently duplicate) broken pre-existing helpers encountered while reading the target test file. Embedded to `reflections` collection.
