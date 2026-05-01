---
date: "2026-05-02"
issue: 292
pr: 304
category: agent
targets:
  - ".github/agents-copilot/test-writer.agent.md"
  - ".github/notes/gotchas.md"
severity: minor
---

## New pipeline phase silently exhausts mock `side_effect` slots in orchestrator tests

### Finding

When `StoryFoundationAgent` was added as the first pipeline phase in PR #304, three existing orchestrator tests broke because they mocked `provider.generate_text` with a fixed `side_effect=[...]` list. The new phase consumed `side_effect[0]`, shifting every downstream index by 1. Fixing the tests by patching the new agent class (rather than extending the `side_effect` list) resolved all three failures.

A secondary failure occurred in the first patch attempt: the Test Writer placed `foundation_cls.return_value = ...` lines outside the `with (patch(...) as foundation_cls, ...)` context manager block, causing `NameError: name 'foundation_cls' is not defined`.

### Observation

This is a recurring structural risk. Any time a new pipeline phase is inserted before existing phases, every test using an ordered `side_effect` list will silently break. The breakage is non-obvious: no "phase not patched" error is raised — the mock simply returns the wrong response to the wrong phase. The context manager alias issue is a separate, easy-to-introduce mistake when refactoring multi-patch blocks.

### Suggested Improvement

1. Add gotcha #040 to `.github/notes/gotchas.md` documenting the `side_effect` exhaustion pattern and the context manager alias rule.
2. Add a matching guidance block to `.github/agents-copilot/test-writer.agent.md` so future Test Writer dispatches apply the correct patch-class pattern when fixing orchestrator tests after new phases are added.

### Action Taken

Applied:
- Added gotcha #040 (`gotcha-new-pipeline-phase-side-effect-exhaustion-040`) to `.github/notes/gotchas.md` under the Testing section.
- Added "New pipeline phase breaks existing orchestrator tests" guidance block to `.github/agents-copilot/test-writer.agent.md` before the "Stale documentation sweep" block.
