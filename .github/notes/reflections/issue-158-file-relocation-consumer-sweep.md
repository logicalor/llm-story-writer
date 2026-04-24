---
date: "2026-04-24"
issue: 158
pr: 167
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## File relocation consumer sweep misses source-file comments and notes directory

### Finding

PR #167 relocated 11 agent `.md` files from `.opencode/agents/` to `prompts/agents/`. The Coder updated `docs/` and `src/` call sites but left four stale references intact:

1. `README.md` (root) — line 189 still read "Agents (.opencode/agents/)"
2. `AGENTS.md` (root) — line 28 still read "defined in `.opencode/agents/`"
3. `.github/notes/architecture.md` — lines 112–118 described agents at old paths
4. `src/tools/savepoint_manager.py` — a `CANONICAL_PHASES` maintenance comment cited `.opencode/agents/story-orchestrator.md`

All four were caught and fixed during the synthesized review before merge.

### Observation

The Coder's Rule 6 says grep "the entire workspace... including documentation files (`.md`), READMEs, and config files." That instruction, taken at face value, covers surfaces 1–3 (they are all `.md` files). Surface 4 is the genuine gap: the savepoint comment is inside a **`.py` source file that was not modified** by the relocation. Rule 7's inline-comment check applies only to "modified files" — unmodified source files containing path references fall into a blind spot between the two rules.

Similarly, `.github/notes/` is technically covered by "documentation files (.md)" but the Coder's mental model of "docs" gravitates toward `docs/` and root-level READMEs, not the internal knowledge base. Explicitly naming `.github/notes/` removes the ambiguity.

This is the fourth occurrence of the stale-references-after-relocation class:
- Issue #5 → Rule 6 strengthened to grep entire workspace
- Issue #30 → Rule 6 extended to include filenames/directory names
- Issue #156 → (unrelated — chunked outline consolidation)
- Issue #158 → source-file comment gap exposed

### Suggested Improvement

Add a sub-bullet to Rule 6 in `coder.agent.md` explicitly covering:
- Source files (`.py`, `.ts`) as a grep surface during file relocation
- `.github/notes/` as an explicitly named high-risk surface
- The grep command pattern for exhaustive coverage

### Action Taken

Applied: added sub-bullet "**When relocating files**" to Rule 6 in `.github/agents/coder.agent.md` enumerating the four missed-surface types and providing the canonical multi-extension grep command.
