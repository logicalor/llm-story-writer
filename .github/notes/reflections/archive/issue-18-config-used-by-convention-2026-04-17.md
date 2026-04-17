---
date: "2026-04-15"
issue: 18
pr: 64
category: skill
targets:
  - ".github/skills/"
severity: minor
status: active
---

## "Used By" column in skill config tables prevents config key ambiguity

### Finding

During issue #18 (Build Outline Planner Subagent), the Synthesized Review finding U-W-01 identified that the `outline-structure` skill's config table had ambiguous keys: `outline_max_revisions` vs `outline_critique_iterations` could mean the same thing, and it was unclear which agent consumed which key. The fix added a "Used By" column to the config table, clarifying that `outline_max_revisions` is consumed by the orchestrator while `outline_critique_iterations` is consumed by the planner.

### Observation

When skills define config keys consumed by multiple agents (e.g., an orchestrator and a subagent), the key names alone can be ambiguous — especially when different agents use different terminology for similar concepts (revisions vs iterations). The "Used By" column makes the consumption relationship explicit, preventing agents from using the wrong config key.

This pattern is analogous to the "Source" column in documentation tables — it traces provenance. For config tables, "Used By" traces consumption. Both help readers understand which component owns or depends on a given value.

This convention should be applied to future skill config tables that define keys consumed by multiple agents. It's a minor authoring convention, not a structural change.

### Suggested Improvement

When the conventions collection and `patterns.md` are created (per issue #7 reflection), add this entry:

```markdown
### Skill Config Table — "Used By" Column

When a skill defines config keys consumed by multiple agents (orchestrator + subagent, writer + reviewer, etc.), add a "Used By" column to the config table mapping each key to its consuming agent. Prevents ambiguity when different agents use different terminology for similar concepts.
```

No file to apply this to currently — recording for inclusion when `patterns.md` is created.

### Action Taken

No action taken — target file (`patterns.md`) does not exist yet. Recorded as a reflection for inclusion when the conventions collection is created (issue #7 dependency).
