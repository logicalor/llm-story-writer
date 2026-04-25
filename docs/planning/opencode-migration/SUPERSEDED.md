# OpenCode Migration Planning — Superseded

**Date:** 2026-04-25
**Status:** Superseded by ADR 007

## Summary

The OpenCode agentic architecture (documented in this directory) was fully superseded by the Python-native orchestration and TUI described in [ADR 007](../adr/007-python-native-orchestration.md). All ten migration tasks have been completed across issues #158–#166.

## References

- [ADR 007: Python-Native Orchestration and TUI](../adr/007-python-native-orchestration.md) — authoritative architecture decision
- [PRD: OpenCode Agentic Architecture Migration](./prd.md) — original requirements (historical)
- [Task Breakdown](./tasks.md) — all tasks and completion status (historical)

## Migration Issues

| Issue | Task |
|-------|------|
| #158 | Task 1: Relocate agent system prompts and add frontmatter-stripping loader |
| #159 | Task 2: Add AsyncOpenAI-based streaming model provider |
| #160 | Task 3 & 4: Define typed pipeline handoff objects; build approval gate and streaming bus primitives |
| #161 | Task 5: Build Python pipeline orchestrator (headless) |
| #162 | Task 6 & 7: Wire CLI entry points and remove legacy stub; delete TypeScript tool wrappers |
| #163 | Task 8: Build Textual TUI shell with streaming output and approval gate |
| #164 | Task 9: Remove OpenCode runtime artefacts and update build configuration |
| #166 | Task 10: Update documentation and mark the OpenCode plan as superseded |

This condensed historical summary tracks the first ten Python-native migration tasks. For the authoritative task breakdown and expanded post-migration task list, see [../python-native-migration/tasks.md](../python-native-migration/tasks.md).

The ADR 001 hybrid agent-tool architecture has been retired. The repository no longer contains any `.opencode/`, `opencode.json`, `package.json`, or TypeScript files.