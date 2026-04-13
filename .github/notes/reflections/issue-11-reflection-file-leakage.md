---
date: "2026-04-13"
issue: 11
pr: 36
category: agent
targets:
  - ".github/agents/orchestrator-v3.agent.md"
severity: major
status: active
---

## Reflection files from prior issues leak into subsequent PRs

### Finding

During issue #11 (Build setting-mgr Tool), two reflection files from issue #6 (`issue-6-boundary-validation-depth.md`, `issue-6-coder-pattern-amnesia.md`, `issue-6-python-falsy-default-antipattern.md`) were present as untracked files in the working tree and got included in the issue #11 commit. These files were created by the Reflection agent during issue #6's Step 8 but were never committed as part of that step.

### Observation

The Orchestrator's Step 8 says "Run `git status` to check for uncommitted changes. If uncommitted changes exist, commit and push." This instruction is correct but relies on the session completing Step 8 fully. If the session ends before the commit (timeout, context exhaustion, user interruption), reflection files remain as untracked `??` entries and silently get swept into the next issue's commit via `git add -A`.

Two gaps:
1. **Step 8 (Reflect):** No explicit instruction to `git add` reflection files specifically — relies on the generic "commit all uncommitted changes" which can miss untracked files if the session ends prematurely.
2. **Step 5d (Working Tree Audit):** The audit checks for `??` untracked files but has no guidance on identifying files from *prior issues* that shouldn't be in the current commit — specifically `.github/notes/reflections/` files not matching the current issue number.

### Suggested Improvement

Add a check to the Orchestrator's Step 5d (Working Tree Audit), after the existing `??` inspection guidance:

```markdown
- **`.github/notes/reflections/`** — check for reflection notes from *prior* issues (filenames containing a different issue number than the current task). These are leftovers from incomplete Step 8 in a previous session. Commit them separately with message `chore: commit orphaned reflection notes` before the main implementation commit, or stage them explicitly as part of the current commit with a note in the PR comment.
```

### Action Taken

Proposed for approval — modifies Orchestrator Step 5d workflow.
