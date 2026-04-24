---
date: "2026-04-25"
issue: 162
pr: 172
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## Sweep `prompts/agents/` when deleting TypeScript tool wrappers

### Finding

PR #172 deleted 17 TypeScript tool wrappers from `.opencode/tools/`. Post-merge review
identified that `prompts/agents/story-orchestrator.md` and sibling agent prompt files still
contain references to the deleted tool names in their workflow step prose and tool-call examples.
These stale references were tracked as follow-up issue #173.

The deletion sweep in the Coder rules (Rule 6) does not currently mention `prompts/agents/`
as a high-risk surface when deleting TypeScript tool wrappers.

### Observation

Agent prompt files are the runtime authority for agent behaviour — they describe which tools to
call, the operation names, and parameter shapes. A deleted tool that still appears in a prompt
file causes a live agent to attempt tool calls that will fail at runtime (tool not found). The
failure surface is invisible to lint and grep sweeps scoped to `src/` or `.opencode/tools/`.

The `prompts/agents/` directory is already identified as a high-risk surface in other deletion
scenarios (Rule 6 "When removing a provider type…" bullets cover docs), but it is not
explicitly called out for tool wrapper deletion.

### Suggested Improvement

Add a new "When deleting TypeScript tool wrappers" bullet to Coder Rule 6 in
`.github/agents/coder.agent.md` mandating a sweep of `prompts/agents/` and `.github/agents/`
for references to the deleted tool names.

### Action Taken

Applied: added "When deleting TypeScript tool wrappers" bullet to Coder Rule 6 in
`.github/agents/coder.agent.md` requiring a grep sweep of `prompts/agents/` and
`.github/agents/` after tool wrapper deletion, with source attribution to issue #162, PR #172
and follow-up issue #173.
