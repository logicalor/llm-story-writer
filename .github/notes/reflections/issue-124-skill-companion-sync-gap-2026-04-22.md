---
date: "2026-04-22"
issue: 124
pr: 130
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

<!-- Archived. Full note in archive/issue-124-skill-companion-sync-gap-2026-04-22.md -->

## New pipeline subagent added without updating story-pipeline/SKILL.md companion

### Finding

During PR #130 (feat/issue-124-story-planner-agent), the `story-planner` subagent was implemented with correct `opencode.json` registration but the `story-pipeline/SKILL.md` companion skill was not updated. All three reviewers independently flagged this as the blocking critical finding (U-C-01) before merge. The SKILL still declared "These are the only eight subagents the orchestrator may dispatch" — an authoritative constraint that would cause a compliant orchestrator reading the skill to refuse dispatching `story-planner` at Phase 2.5, silently skipping the entire narrative arc analysis pass.

This is the third occurrence of the same pattern:
- **Issue #23** — compaction plugin not registered in `opencode.json` → led to Coder Rule 10
- **Issue #120** — `quality-reviewer` added, SKILL.md still read "only four subagents" after PR added a fifth → led to review checklist companion-sync item
- **Issue #124** — `story-planner` added, SKILL.md still read "only eight subagents" after PR — CAUGHT by review, not prevented by Coder

The Coder Rule 10 already handles `opencode.json` registration. The review checklist already has a companion-sync item downstream. The gap is the **upstream Coder rule**: no sub-bullet instructs the Coder to update the SKILL alongside writing the agent file.

### Observation

The review system detected this correctly (unanimously Critical), but the detection cost a full review cycle before the fix could land. The root cause is absence of a Coder-side prevention rule. Adding a specific sub-bullet to Rule 10 makes the omission structurally harder — the Coder will see the obligation at the same moment it reads the opencode.json registration sub-bullet.

The pattern affects specifically "story pipeline subagents" — agents that represent a named phase in the narrative generation pipeline. Not every `.opencode/agents/*.md` file triggers this (workflow agents like Coder or Orchestrator are not in the story pipeline). The sub-bullet should target the specific subtype.

### Suggested Improvement

**Coder Rule 10 — add a story pipeline sub-bullet immediately after the `opencode.json` agents sub-bullet:**

> - **New story pipeline subagents specifically:** When the new agent represents a named story pipeline phase (e.g., `story-planner`, `chapter-outline-expander`), also update `.opencode/skills/story-pipeline/SKILL.md` in the same commit: (a) add a Phase Definition entry; (b) add a row to the Subagents table; (c) update the pipeline diagram to show the new phase; (d) update the authoritative constraint sentence to the new count ("These are the only N subagents..."). The SKILL is the runtime authority for pipeline rules — an orchestrator reading a stale SKILL may refuse to dispatch the new agent and silently skip the phase. This is a third-occurrence pattern (issues #23, #120, #124); every new pipeline subagent has triggered it.

### Action Taken

Applied: Added story pipeline subagents sub-bullet to Coder Rule 10, immediately after the `opencode.json` agents sub-bullet, before the Schema conformance sub-bullet.
