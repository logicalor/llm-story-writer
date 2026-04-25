# OpenCode Migration Planning — Superseded

**Date:** 2026-04-25
**Status:** Superseded by ADR 007

## Summary

The OpenCode agentic architecture (documented in this directory) was fully superseded by the Python-native orchestration and TUI described in [ADR 007](../adr/007-python-native-orchestration.md). All nine migration tasks have been completed across issues #158–#166.

## References

- [ADR 007: Python-Native Orchestration and TUI](../adr/007-python-native-orchestration.md) — authoritative architecture decision
- [PRD: OpenCode Agentic Architecture Migration](./prd.md) — original requirements (historical)
- [Task Breakdown](./tasks.md) — all tasks and completion status (historical)

## Migration Issues

| Issue | Task |
|-------|------|
| #158 | Task 1: Relocate agent system prompts and add frontmatter-stripping loader |
| #159 | Task 2: Add AsyncOpenAI-based streaming model provider |
| #160 | Task 3: Define typed pipeline handoff objects |
| #161 | Task 4: Build headless Python orchestrator with savepoints |
| #162 | Task 5: Wire CLI entry point and remove TypeScript tool wrappers |
| #163 | Task 6: Build Textual TUI with streaming output |
| #163 | Task 7: Chapter outline expander |
| #164 | Task 8 & 9: Remove remaining OpenCode artefacts |
| #165 | Task 9: Remove Node.js artefacts |
| #166 | Task 10: Documentation cleanup (this issue) |

The ADR 001 hybrid agent-tool architecture has been retired. The repository no longer contains any `.opencode/`, `opencode.json`, `package.json`, or TypeScript files.