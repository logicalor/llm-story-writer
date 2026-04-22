---
date: "2026-04-22"
issue: 125
pr: 131
category: agent
targets:
  - ".github/agents/_shared/code-review-process.md"
severity: minor
status: archived
---

## Review checklist missing story-pipeline SKILL.md companion sync check for new subagents

### Finding

During PR #131 (feat/issue-125-analytical-review-family), the synthesis review unanimously
identified that `story-pipeline/SKILL.md` was not updated when `consistency-checker` was
added as a new pipeline subagent. The constraint sentence on line 190 — "These are the only
[N] subagents the orchestrator may dispatch" — omitted `consistency-checker`, making the
finding Critical (not merely a documentation warning) because an orchestrator loading the
stale SKILL.md will refuse to dispatch the unlisted agent.

The review caught this finding correctly. However, the `code-review-process.md` structural
checklist has an explicit item for `opencode.json` registration (added from issue #123) but
no corresponding item for `story-pipeline/SKILL.md` companion sync. This asymmetry means:

- The `opencode.json` registration check is explicitly prompted by name → consistently
  checked by all models (all three unanimously found the missing registration in PR #131).
- The SKILL.md companion sync relies on the "Companion file concept sweep" heuristic
  (line 46) — a general instruction rather than a named, triggered check — which two of
  three models originally classified as Warning rather than Critical.

### Observation

The Coder rule from issue #124 already instructs the Coder to update
`story-pipeline/SKILL.md` alongside the new agent file. But the review process needs its
own explicit downstream check — just as `opencode.json` registration has one — so that
reviewers are told exactly what to read and what to verify, rather than relying on the
general companion sweep to surface a Critical blocker.

The pattern has recurred in issues #120, #124, and #125 — every new story pipeline subagent
has triggered this finding. An explicit checklist item removes the dependency on reviewer
inference.

### Suggested Improvement

Add a checklist item to `code-review-process.md` Phase 1 structural review, immediately
after the `opencode.json` registration item, before "Shell snippet safety":

```
- [ ] **`story-pipeline` SKILL.md sync for new pipeline subagents** — when any
  `.opencode/agents/*.md` file that represents a named story pipeline phase is **added**,
  also read `.opencode/skills/story-pipeline/SKILL.md` directly and verify: (1) a Phase
  Definition entry exists for the new phase; (2) the new agent has a row in the Subagents
  table; (3) the pipeline diagram includes the new phase; (4) the authoritative constraint
  sentence ("These are the only N subagents the orchestrator may dispatch") names the new
  agent and uses the updated count. This file is never in the diff — it must be read
  explicitly. A stale constraint sentence actively prevents dispatch: an orchestrator
  loading the SKILL.md will refuse to call the unlisted agent. Recurrence pattern:
  issues #120, #124, #125.
```

### Action Taken

Applied: Added `story-pipeline` SKILL.md sync checklist item to
`.github/agents/_shared/code-review-process.md`, immediately after the `opencode.json`
registration item and before "Shell snippet safety".
