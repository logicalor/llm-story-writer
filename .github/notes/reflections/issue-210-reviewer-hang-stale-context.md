---
date: "2026-04-27"
issue: 210
pr: 216
category: agent
targets:
  - ".github/agents/orchestrator-v3.agent.md"
  - ".github/agents/synthesizing-reviewer.agent.md"
severity: minor
status: active
---

## Reviewer sub-agent hang and stale-context divergence in partial synthesis

### Finding

During PR #216's review cycle, two distinct reviewer failure modes occurred:

1. **GLM reviewer hung in a search loop** and never completed its report. The Orchestrator proceeded with Qwen and Kimi only, producing a 2-model synthesis.

2. **Qwen reported findings based on stale code** — a `sys.exit(1)` leak and a lazy import violation — that had already been fixed in the current branch. Kimi correctly identified both as already resolved. The Divergence Analysis correctly downgraded Qwen's findings.

### Observation

The Orchestrator Phase B instructs sequential dispatch of three reviewers but provides no timeout, abandonment, or partial-input rules. The Synthesizing Reviewer Step 1 does say to proceed with available reports, but the Orchestrator has no explicit trigger for invoking it with incomplete input.

The stale-context divergence is handled correctly by Step 3 (Divergence Analysis) when a 2-vs-1 split occurs, but there is no explicit false-positive filter for "reviewer is operating from outdated codebase understanding." Without a filter, the Synthesizing Reviewer must independently decide to verify the current file — which it did, but this relies on model initiative rather than protocol.

### Suggested Improvement

1. **Orchestrator Phase B** — add reviewer hang/abandonment guidance after the dispatch order list:
   > If a reviewer sub-agent does not complete within a reasonable time or appears stuck in a repeated tool-call loop, proceed with the reports that have been written to disk. Do not block the review cycle indefinitely. If at least two reviewers have completed, dispatch the Synthesizing Reviewer with partial input. If fewer than two reviewers complete, retry the hung reviewer once before escalating to the user.

2. **Synthesizing Reviewer Step 2** — add a false-positive filter for stale reviewer context:
   > **Stale reviewer context filter:** If one reviewer reports a defect (e.g., `sys.exit` leak, import convention violation, missing guard) and another reviewer states that the defect was already fixed in a previous round or does not exist in the current branch, verify the claim by reading the actual file on disk. Reviewers occasionally operate from stale context about the codebase. If the current file does not contain the alleged defect, downgrade the finding to "already fixed — stale reviewer context" and exclude from consensus counts.

3. **Synthesizing Reviewer output format** — when only two of three reviewers contributed, cap the Model Agreement Score at 7/10 to signal reduced coverage confidence.

### Action Taken

Applied:
1. Added **reviewer hang / partial input rule** to Orchestrator Phase B after the dispatch order list (`.github/agents/orchestrator-v3.agent.md`).
2. Added **stale reviewer context filter** to Synthesizing Reviewer Step 2 (`.github/agents/synthesizing-reviewer.agent.md`).
3. Added **partial-synthesis confidence cap** note to the output format's Model Agreement Score guidance (`.github/agents/synthesizing-reviewer.agent.md`).
