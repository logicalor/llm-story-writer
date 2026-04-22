---
date: "2026-04-23"
issue: 135
pr: 142
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: active
---

## Savepoint resume path omits state write-back — state permanently out of sync

### Finding

During issue #135 (PR #142, `feat/issue-135-scene-writer-generate-chapter`), the `cmd_generate_chapter` function implemented a savepoint fast-path (`if _has_savepoint(repo, step): return content`) that loaded cached content and returned it immediately without writing the result back to `story_state`. The full generation path did write back to story state (via `_set_nested` + `_write_state_atomic`). On first run, story state was populated correctly. On any resumed run (savepoint already present), story state was never updated. Any downstream operation reading state (e.g. a recap generator reading `chapters.N.content`) would find the field absent — as if generation had never run — causing silent data loss or wrong output. The bug was caught during code review; the PR fixed it by adding the write-back to the resume path.

### Observation

The Coder has guidance about savepoint *ownership* (subagents must not call savepoint-mgr directly) and about savepoint *expectation drift* (tests asserting old savepoint key names must be updated). There is no guidance about **symmetric write obligations**: when a function writes to story state in its primary path, its savepoint resume path must perform the same write. The resume path is perceived as a cache hit — "we already did the work, just return it" — and the story-state write looks like "work", so it gets skipped. This is the wrong mental model: story state and savepoints are separate stores that must stay in sync.

### Suggested Improvement

Add a named guidance block for savepoint resume symmetry to the Coder's "Code Patterns" section, after the "Story state JSON loading" block:

```markdown
**Savepoint resume write symmetry:** When an operation writes results to story state (via `_set_nested` + `_write_state_atomic` or equivalent), its savepoint resume path must perform the same write. A resume path that loads from a savepoint and returns immediately without updating story state leaves the two stores out of sync: downstream operations reading state see a missing field even though the savepoint exists. Pattern: load content from savepoint → write to story state → return. Do not treat the resume path as "cache hit, skip side-effects" — the story-state write is not a side-effect of generation; it is a required synchronisation step.
```

### Action Taken

Applied: added "Savepoint resume write symmetry" named block to the Code Patterns section of `.github/agents/coder.agent.md`, after the "Story state JSON loading" block.
