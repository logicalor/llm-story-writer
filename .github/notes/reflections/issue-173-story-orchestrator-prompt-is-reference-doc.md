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

## StoryOrchestratorAgent is vestigial — story-orchestrator.md is reference documentation, not a runtime system prompt

### Finding

`src/presentation/agents/story_orchestrator.py` contains a `StoryOrchestratorAgent` class but does not call `load_agent_prompt()`. This means `prompts/agents/story-orchestrator.md` is **not** injected as a system prompt at runtime. The file functions as reference documentation and a design specification for the pipeline — not a live agent instruction set.

### Observation

Without a clear status marker, the file appears to be a runtime agent prompt (it has a YAML frontmatter `mode: primary` block and is structured like other agent prompts that *are* loaded at runtime). A contributor or agent referencing the file without checking the Python class could incorrectly assume the instructions are executed automatically.

This is especially relevant now that the Python-native migration is underway (ADR 006): other agent prompts may be loaded at runtime while this one is not, creating an invisible divergence in how prompts operate.

### Suggested Improvement

Add a runtime status note to the `## Architecture` section of `story-orchestrator.md` to document that the Python class does not load this file at runtime.

### Action Taken

Applied: added a `> **Runtime status:**` blockquote to the `## Architecture` section in `prompts/agents/story-orchestrator.md` documenting that `src/presentation/agents/story_orchestrator.py` does not call `load_agent_prompt()` and the file serves as reference documentation.
