---
date: "2026-04-14"
issue: 16
pr: 52
category: agent
targets:
  - ".github/agents/orchestrator-v3.agent.md"
severity: major
status: archived
---

## Orchestrator Step 5d lacks commit scope validation — line-ending contamination inflated PR

### Finding

During issue #16 (PR #52), the first commit included 72 modified `legacy/` files and 78 other files with line-ending differences from the development branch. These were not functional changes — they were whitespace/line-ending normalisation artefacts picked up by `git checkout`. The Synthesized Review flagged them (★★☆, majority), and they had to be reverted in a follow-up commit.

Root cause: no `.gitattributes` in the repository, no pre-commit hook normalising line endings, and the Orchestrator's Step 5d working tree audit only checks for **untracked** files (`??` in porcelain output). It does not validate that the **set of modified files** is within the expected scope of the task.

### Observation

This is the second scope-inflation pattern observed. Issue #5 had auto-formatting changes mixed with functional commits (addressed by Coder Rule 8). Line-ending contamination is a different vector — Coder Rule 8 covers auto-formatter output, but line-ending differences are silent git-level artefacts that appear as modified files without the Coder ever opening them.

The Orchestrator is the correct place for this check because the Coder may not be aware of scope inflation in files it never touched — the contamination happens at the git layer, not the editing layer.

### Suggested Improvement

Add a **scope validation check** to Orchestrator Step 5d, after the existing untracked-file audit and before the commit command:

```markdown
**Scope validation:** Before committing, verify the changed file set matches expectations:

```bash
git diff --stat | tail -1
```

If the number of changed files significantly exceeds what the task should have touched, inspect the full `git diff --stat` output. Common causes of scope inflation:

- **Line-ending changes** in files never edited (no `.gitattributes` normalisation)
- **Auto-formatter changes** in files outside task scope (see Coder Rule 8)
- **Unintended submodule updates**

Revert unrelated changes before committing:

```bash
git checkout -- path/to/unrelated/file
# or for entire directories:
git checkout -- legacy/
```
```

Additionally, add `.gitattributes` to the repository as a follow-up task (add to deferred.md):

```
* text=auto
*.py text eol=lf
*.md text eol=lf
*.sh text eol=lf
```

### Action Taken

Proposed for approval — this adds a new validation step to the Orchestrator's commit workflow (Step 5d), changing the agent's behaviour. Collated 2026-04-17, pending user approval.
