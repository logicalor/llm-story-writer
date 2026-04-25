---
date: "2026-04-25"
issue: 164
pr: 175
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## `prompts/agents/` not in explicitly named high-risk surfaces for relocation sweep

### Finding

PR #175 deleted `.opencode/` and relocated skill files to `prompts/skills/`. The Coder ran a reference sweep but missed two agent prompt files — `prompts/agents/final-editor.md` and `prompts/agents/prose-scrubber.md` — which still referenced the deleted `.opencode/` path. The fixes were two line changes, but they required a full review cycle to catch.

The existing "When relocating files" sub-bullet in Rule 6 of `coder.agent.md` already says to grep `*.md` files and explicitly names `AGENTS.md` and `.github/notes/` as high-risk surfaces. `prompts/agents/` is not in that list, even though runtime agent prompt files routinely reference internal directory paths and technology-specific tool locations.

### Observation

The "When deleting TypeScript tool wrappers" sub-bullet already knows about `prompts/agents/` (it says to sweep there for deleted tool names). The "When relocating files" sub-bullet does not cross-reference this surface. The gap is systematic: any deletion or relocation of a path inside `.opencode/` or any other tool/skill directory should trigger a `prompts/agents/` sweep, not just TS wrapper deletions.

Adding `prompts/agents/` to the explicitly named high-risk surfaces closes the gap. Stale references in agent prompt files are particularly harmful because they silently mislead the executing agent — no linter, type checker, or test covers them.

### Suggested Improvement

Add `(d) prompts/agents/` to the explicitly named high-risk surfaces list in the "When relocating files" sub-bullet of Rule 6 in `.github/agents/coder.agent.md`, noting that runtime agent prompt files reference directory paths and technology-specific tool locations.

### Action Taken

Applied: added entry `(d)` for `prompts/agents/` to the high-risk surfaces list in the "When relocating files" sub-bullet of Rule 6; also added issue #164 / PR #175 to the source attribution.
