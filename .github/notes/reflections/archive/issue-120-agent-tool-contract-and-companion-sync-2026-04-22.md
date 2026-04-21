---
date: "2026-04-22"
issue: 120
pr: 127
category: instruction
targets:
  - ".github/agents/_shared/review-checklist.md"
severity: minor
status: archived
---

## Agent tool-contract validation and orchestrator-companion sync absent from review checklist

### Finding

PR #127 (Quality Reviewer subagent extraction) entered review with six actionable defects that required a full revision cycle before merge. All six were fixed before merge, but five of the six represent defect classes not currently checked by the shared review checklist (`review-checklist.md`):

1. **`parse-scores` contract mismatch** — Step 2b instructed the agent to call `critique-runner` with `operation: "parse-scores"`, `name`, and `iteration`. The actual operation requires `--critic-type` and `--response-text` to parse a raw LLM response; it does not accept aggregate savepoint reads. The loop would fail with exit code 2 on the first iteration. This is a tool contract error in a new agent instruction file, not in an edit to an existing one.

2. **`mode: "chapter"` omission** — Every `critique-runner` invocation in the new agent omitted `mode: "chapter"`. The tool defaults to `mode: "outline"`, so the entire loop would silently evaluate the wrong artifact type. This is a non-obvious tool default trap not caught by any current review item.

3. **`best_chapter_text` never stored** — `best_score` was tracked but the associated chapter text was not preserved. The accepted result would return the *latest* revision, not the *best-scoring* revision, violating the documented architectural guarantee. Finding [M-C-03] confirmed by all models, elevated to Critical because the feature docs explicitly promise best-version semantics.

4. **Missing `data` parameter on `savepoint-mgr` save** — Step 2g called `savepoint-mgr` save without specifying a `data` value. The Python CLI enforces `--data` as required for save and exits with an error if absent. A new required parameter was missed in the agent instruction.

5. **`story-pipeline/SKILL.md` companion drift** — The SKILL.md still read "four subagents" and "only four subagents" after the PR added a fifth. Any orchestrator session loading this skill would receive a false authoritative constraint blocking dispatch of the new agent.

6. **Savepoint naming convention** — The savepoint step used `/` as a hierarchical separator (`chapter_{N}/quality_revision_{M}`) while all other project savepoints use underscore separators. Caught by the Gemini style finding [S-I-01].

### Observation

Finding (1) is a new instance of the established tool-schema-fabrication defect class (issues #19, #22, #113, #115). The difference here is that it appeared in a *newly authored* agent instruction file rather than in an edit to an existing file. Coder Rule 10 (extended in issues #113 and #115) addresses verifying parameters *when editing existing content*. The rule wording was broadened in issue #115 to cover "writing or editing any agent or skill content", but this coverage has not propagated into the shared review checklist — so reviewers have no explicit checklist gate for this class of error when reviewing new agent files.

Finding (2) is a variant: the tool parameter was not wrong — it was *omitted* because the default appeared safe. A tool default designed for a different context (outline mode) silently misbehaves in a chapter context. This is distinct from a wrong value or misspelled key; it requires checking tool defaults explicitly for each omitted parameter.

Finding (5) is the companion-file drift pattern from issues #113, #115, and #117. The existing code-review-process.md Phase 1 "Companion file concept sweep" covers the case where an *operation name or parameter name* changes and needs to be swept. It does not cover the case where a PR *adds a new subagent to the orchestrator* and the companion SKILL.md reference table and constraint sentence require a count update — those are additive changes, not concept renames.

All five defect classes are preventable at review time by explicit checklist items. The items are missing from `review-checklist.md` (the checklist used by reviewers during Phases 2 and 7), even though the underlying patterns have been codified in `coder.agent.md` and `code-review-process.md` for related but narrower use cases.

Model agreement was notably low (4/10). Claude missed the two most severe runtime defects; GPT missed the SKILL.md companion gap; Gemini had the broadest coverage but was the only one to catch the missing `data` parameter. The low consensus is a signal that tool-contract class defects are actively missed by reviewer models without checklist scaffolding.

### Suggested Improvement

**Change 1 — review-checklist.md Phase 2: new "Agent Instructions" subsection**

Add after the existing "Data Access" subsection in Phase 2:

```
#### Agent Instructions

- [ ] **Tool call contracts** — for any new or modified agent instruction file that includes tool invocations, verify each call against the tool source before accepting: (a) operation names match Python CLI dispatch (grep `src/tools/*.py` for valid operation values), (b) parameter key names match Zod field names in the TS wrapper (`.opencode/tools/*.ts`) — mismatched keys pass Zod silently; (c) any omitted parameter is confirmed safe — check the tool's default value and verify it produces correct behaviour in this context (e.g. `mode` defaults to `"outline"` in `critique-runner`; a chapter-context agent that omits `mode` will evaluate the wrong artifact type without erroring)
```

**Change 2 — review-checklist.md Phase 7: orchestrator-companion sync item**

Add a new item to the Phase 7 Documentation Review checklist:

```
- [ ] **Orchestrator-subagent companion sync** — if this PR adds or removes a subagent dispatch in the orchestrator, verify `story-pipeline/SKILL.md` is updated: (1) the subagent count in the overview sentence ("The pipeline uses N subagents"), (2) the reference table row, and (3) the constraint sentence ("These are the only N subagents the orchestrator may dispatch"); a stale constraint is an authoritative false statement that blocks dispatch of the new agent
```

### Action Taken

Applied: Added "Agent Instructions" subsection (tool call contracts item) to Phase 2 of `review-checklist.md`. Added "Orchestrator-subagent companion sync" item to Phase 7 of `review-checklist.md`. Removed stale active copy of `issue-122-table-without-prose-parity.md` (already archived).
