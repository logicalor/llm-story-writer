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

## OpenCode hard rule existed only in story-orchestrator.md — migration scope confirmed correct

### Finding

During PR #179, all 13 agent prompts in `prompts/agents/` were audited for OpenCode-specific "Tool Usage — Hard Rule" sections. Only `story-orchestrator.md` contained one. The remaining 12 files (`outline-planner.md`, `character-sheet-generator.md`, `chapter-writer.md`, `wiki-maintainer.md`, `quality-reviewer.md`, `story-planner.md`, `consistency-checker.md`, `prose-scrubber.md`, `final-editor.md`, `chapter-outline-expander.md`, `regenerate.md`, `continue.md`) had no TS-specific hard rules.

### Observation

The Python-native migration (ADR 006) touched agent prompts incrementally. Only `story-orchestrator.md` retained an OpenCode-specific "Tool Usage — Hard Rule" section, likely because it was one of the earlier and more fully specified agent prompts written during the OpenCode era. The finding validates the narrow scope of PR #179 — no other prompt files required parallel updates for this specific rule type.

This also confirms a useful audit pattern: when removing a class of stale content (e.g., "OpenCode hard rules"), a full directory grep before filing the issue prevents under-scoped PRs.

### Suggested Improvement

No action needed. This note confirms the migration scope was correct and complete for this class of stale reference. Future migration work that targets a specific pattern should follow the same full-directory audit before scoping the issue.

### Action Taken

No action needed — scope confirmed correct.
