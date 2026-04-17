---
date: "2026-04-17"
issue: 27
pr: 87
category: agent
targets:
  - ".github/agents/orchestrator-v3.agent.md"
severity: minor
status: archived
---

## git-safe-publish.sh and verify-green.sh do not exist — removed from orchestrator

### Finding

During issue #27 (Task 25: End-to-End Integration Test with Wiki), `scripts/git-safe-publish.sh` was called per the Orchestrator's Step 5d, Step 7, and Step 8 instructions. The script does not exist: `scripts/git-safe-publish.sh: No such file or directory`. Standard `git add -A && git commit -m "..." && git push origin {branch}` commands were used as a fallback.

Similarly, `scripts/verify-green.sh` (referenced in Step 7 Phase D) does not exist. Both scripts are tracked in `.github/notes/deferred.md` as items not yet created.

### Observation

This is the **9th+ occurrence** of the `git-safe-publish.sh` friction. Prior reflections (issues #1, #4, #11, #16, #21, #59, #69, and now #27) have recorded it as a recurrence each time without resolving it. The deferred item has accumulated without resolution for the full duration of the project.

Rather than continuing to defer script creation, the cleaner path is to remove the script references from the orchestrator entirely and replace them with direct `git` commands. The direct commands (`git add -A && git commit -m "..." && git push origin {branch}`) are well-understood, always available, and accomplish the same goal. The scripts add a layer of indirection without providing unique value that isn't achievable with standard git.

The one capability the script had was looping to handle pre-commit hook auto-fixes. This can be handled in-line with a note: if pre-commit hooks auto-modify files, run `git add -A && git commit --amend --no-edit` then push again.

### Suggested Improvement

Replace all four `bash scripts/git-safe-publish.sh "..."` occurrences in the orchestrator with:

```bash
git add -A && git commit -m "..." && git push origin {branch-name}
```

Replace `bash scripts/verify-green.sh` with:

```bash
pytest tests/unit/ -v && ruff check . && mypy src/
```

Also remove the descriptive text about what the script does, and remove the `deferred.md` entries for both scripts since they are no longer needed.

### Action Taken

Applied: replaced all `git-safe-publish.sh` and `verify-green.sh` references in orchestrator-v3.agent.md with direct git/pytest commands.
