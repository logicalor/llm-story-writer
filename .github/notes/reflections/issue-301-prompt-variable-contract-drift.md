---
date: "2026-05-02"
issue: 301
pr: 313
category: agent
targets:
  - ".opencode/agents/coder.md"
severity: minor
---

## Prompt variable contract change causes test expectation drift

### Finding

During issue #301 (PR #313), `ChapterWriterAgent._run_scene_pipeline()` was updated to inject
position-specific scene prompts using a new variable set (`current_scene_summary`, `base_context`,
`scene_index`, `total_scenes`, `previous_scene_tail`). The existing test
`test_scene_pipeline_runs_three_stages_in_order` had been asserting that captured scene prompts
contained `"Scene 1"` or `"scene_num"` — variables from the old single generic scene prompt.

After the new prompts were injected, those assertions were stale: the new prompt passes scene
description text (e.g. `"Opening"`, `"Climax"`) rather than index strings. The test required a
second Coder dispatch to update the assertions.

### Observation

The existing Rule 11 "Test expectation drift" guidance in `coder.md` lists examples of output
contracts that change: "savepoint key names, stdout format, internal counts". It does not mention
**prompt variable names** — the set of keys passed to `load_prompt(name, variables)`.

When a prompt template is **replaced** (new name or fundamentally different variable set), any test
that asserts on specific variable names or rendered content from the old template becomes stale.
This is the same class of expectation drift but with a distinct trigger: prompt template
substitution rather than savepoint or stdout changes.

The gap means the Coder did not recognise the stale test as expectation drift and did not fix it
during the main dispatch, causing a follow-up Test Writer re-dispatch to clean it up.

A second, minor finding: `previous_scene_tail` was assigned but then removed from the `variables`
dict during the same refactor, producing ruff `F841` (local variable assigned but never used). This
was caught by lint and handled by the Coder. No guidance change needed — ruff already enforces this.

### Suggested Improvement

Extend the test expectation drift example list in Rule 11 of `.opencode/agents/coder.md` to include
**prompt variable names** as an explicit example category:

> "savepoint key names, stdout format, internal counts, prompt variable names"

This makes it unambiguous that when an implementation changes which variables are passed to
`load_prompt()`, existing tests asserting on the old variable keys/values are expectation drift —
not regressions — and must be updated in the same dispatch.

### Action Taken

Applied: added "prompt variable names" to the test expectation drift example list in
`.opencode/agents/coder.md` Rule 11.
