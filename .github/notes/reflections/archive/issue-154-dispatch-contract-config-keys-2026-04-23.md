---
date: "2026-04-23"
issue: 154
pr: 155
category: agent
targets:
  - ".opencode/agents/story-orchestrator.md"
  - ".opencode/agents/chapter-outline-expander.md"
severity: major
status: archived
---

## Dispatch contracts must include all config values the subagent needs

### Finding

When `story-orchestrator.md` dispatched `chapter-outline-expander`, the three new config keys
added for this feature (`scene_expansion_enabled`, `scenes_per_chapter_min`,
`scenes_per_chapter_max`) were referenced inside `chapter-outline-expander.md`'s body but were
not included in the dispatch parameters sent by `story-orchestrator.md`. The subagent could not
read these keys at runtime, causing scene expansion to silently use default values or fail.

### Observation

Every config value a subagent reads must be passed explicitly at dispatch time. The subagent
cannot read `config.yml` or `story state` independently — it can only read what the orchestrator
provides in the dispatch message. This is a silent failure mode: the subagent runs successfully
but behaves incorrectly because a required config value is missing.

The Input table in the subagent file is the specification of what the dispatch must provide.
If a config key is in the body text but not in the Input table, it is undocumented and will be
omitted by the orchestrator.

### Suggested Improvement

Add a rule to `story-orchestrator.md` (and the relevant shared orchestrator context) stating:

> When adding or modifying a subagent that reads config values, the config keys must be:
> 1. Listed in the subagent's **Input** table, and
> 2. Passed explicitly in the orchestrator's dispatch parameters for that subagent.

Also add a review checklist item to `code-review-process.md` to catch this at review time.

### Action Taken

Approved and archived on 2026-04-23 after adding the dispatch-contract rule to the story pipeline
agent guidance and review checklist.