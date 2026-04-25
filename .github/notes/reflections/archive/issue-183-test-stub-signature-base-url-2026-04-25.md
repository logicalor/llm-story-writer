---
date: "2026-04-25"
issue: 183
pr: 195
category: agent
targets:
  - ".github/notes/gotchas.md"
  - ".github/agents/test-writer.agent.md"
severity: minor
status: archived
---

## Test stubs for _chat_completion must declare base_url keyword argument

### Finding

PR #195 (issue #183) added `base_url: str | None = None` to `_chat_completion`'s signature and
threaded it through production call sites. All five new unit tests for `WikiMaintainerAgent`
defined `_fake_chat_completion` stubs. Review finding S-W-02/S-W-03 identified that any stub
missing `base_url: str | None = None` in its signature would raise `TypeError: unexpected keyword
argument 'base_url'` when the production code called `_chat_completion(prompt, model,
base_url=base_url)`.

The fix was to include `base_url: str | None = None` in every `_fake_chat_completion` stub
across all five test functions.

### Observation

This is a generalisation of an existing pattern: when a shared infrastructure function gains a
new keyword argument, every test stub that patches it must be updated to accept the new kwarg.
Python is permissive about extra `**kwargs` but strict about unexpected keyword arguments against
a fixed-signature stub. The failure mode is loud (TypeError at call time) but only manifests
when that kwarg is actually passed, which may not happen in simpler test cases that exercise
alternative paths.

### Suggested Improvement

1. Add a gotcha entry to `.github/notes/gotchas.md` documenting the stub-signature discipline
   for `_chat_completion` and similar LLM infrastructure functions.
2. Add a brief note to `test-writer.agent.md` under "Write Tests" about keeping test stubs
   signature-compatible when production code gains new kwargs.

### Action Taken

Applied:
- Added gotcha #031 to `.github/notes/gotchas.md` under the "Testing" section.
- Added "Infrastructure stub signature compatibility" note to `test-writer.agent.md`.
