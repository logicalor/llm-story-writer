---
date: "2026-04-25"
issue: 173
pr: 179
category: agent
targets:
  - "prompts/agents/story-orchestrator.md"
severity: minor
status: archived
---

## Pipeline Architecture heading collides semantically with adjacent Architecture heading

### Finding

PR #179 renamed the old "Tool Usage — Hard Rule" section to `## Pipeline Architecture`. This placed the heading at line 10, immediately above `## Architecture` at line 14. The two headings are visually and semantically similar: both relate to how the pipeline is architected. The `## Pipeline Architecture` section contains only a single contextual sentence noting Python implementation; it reads more like a note than an architectural description.

### Observation

Adjacent headings `## Pipeline Architecture` and `## Architecture` are likely to cause scanning confusion. A reader skimming the file may conflate their scopes or skip one. The naming mismatch between the intent of each section (contextual note vs. architecture section) and their heading labels creates unnecessary friction.

The simplest resolution is to rename the shorter note section to something clearly distinct from the structural `## Architecture` heading.

### Suggested Improvement

Rename `## Pipeline Architecture` to `## Implementation Note` to clearly distinguish the contextual note from the adjacent architectural description.

### Action Taken

Applied: renamed `## Pipeline Architecture` to `## Implementation Note` in `prompts/agents/story-orchestrator.md`.
