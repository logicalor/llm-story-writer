---
date: "2026-04-14"
issue: 15
pr: 54
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: active
---

## RRF scores computed as dead code — spec-vs-implementation divergence

### Finding

During issue #15 (Build wiki-snapshot Tool), the Coder implemented Reciprocal Rank Fusion (RRF) scoring as specified in ADR 005. However, the actual relevance formula used a different approach (weighted sum of entity match, metadata, and semantic signals). The RRF computation existed in the code but its output was never integrated into the scoring formula — pure dead code.

### Observation

This is a variant of the dead code pattern (issues #9, #12) but with a different root cause. In prior issues, dead code came from template-copying or abandoned approaches. Here, the dead code came from **implementing both the spec and a working alternative** — the Coder faithfully translated the ADR's RRF specification into code, then separately implemented a formula that actually worked for the use case, without removing the spec-derived code.

This is the **fourth** dead code occurrence (issues #9, #12, #12 again, #15). Coder Rule 7 already covers dead code sweeps. The issue is compliance, not rule text — consistent with the issue #12 reflection's conclusion. The pending semantic verification rule (issue #10) would catch this via data-flow tracing (RRF output is computed but never consumed).

No rule text change needed. Pattern recorded for ChromaDB recall.

### Suggested Improvement

No additional rule text change. The existing Rule 7 (dead code sweep) and pending issue #10 proposal (semantic verification) together cover this pattern. Recording as a data point for the recurring dead code theme.

### Action Taken

No action needed — existing rules sufficient. Recorded for pattern tracking.
