---
date: "2026-04-25"
issue: 182
pr: 194
category: agent
targets:
  - ".github/agents/orchestrator-v3.agent.md"
severity: minor
status: active
---

## Reviewer architectural scope findings waste review time

### Finding

During PR #194, Gemini produced a finding classified as "architectural": the implementation
should use sub-agent delegation rather than inline helper functions. This was structurally
out of scope for the PR (which was a targeted tool enhancement) and was correctly excluded by the
Synthesizing Reviewer. However, Gemini spent material context on elaborating the suggestion, and
the Synthesizer had to document it as a divergence rather than simply skipping it.

### Observation

The reviewer dispatch prompt template in Orchestrator Phase B says "Review all changes on the
current branch against development" with no explicit scope boundary. Reviewers naturally
generalise beyond the PR scope when they identify what they consider an architectural improvement.
This is most pronounced in Gemini, which tends toward higher-abstraction findings.

The Orchestrator already handles out-of-scope findings correctly at triage (Step 7 Phase D):
"create a follow-up GitHub issue capturing the finding". The problem is upstream: reviewer time
is consumed generating the out-of-scope finding in the first place, and the Synthesizer must
process it as an explicit divergence rather than ignore it.

Adding a one-sentence scope constraint to the reviewer dispatch prompt would suppress most
out-of-scope architectural suggestions at generation time.

### Suggested Improvement

Add to the Phase B reviewer dispatch prompt template (after "Follow the shared code review
process at…"):

> "Focus your review on **correctness, security, test coverage, and project convention adherence**
> for the changes in this PR. Do not propose architectural refactors, framework migrations, or
> structural redesigns that are out of scope for this PR — record such observations as
> Suggestions only with a clear note that they are out-of-scope for this change."

### Action Taken

Applied: Added scope constraint sentence to the Phase B reviewer dispatch prompt template in
Orchestrator Step 7.
