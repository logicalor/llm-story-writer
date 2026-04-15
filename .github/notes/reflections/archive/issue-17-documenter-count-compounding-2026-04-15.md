---
date: "2026-04-15"
issue: 17
pr: 61
category: agent
targets:
  - ".github/agents/documenter.agent.md"
severity: minor
status: active
---

## Documenter tool count wrong AND pre-existing missing table entry — compounding errors

### Finding

During issue #17 (Build wiki-lint Tool), the Documenter updated the tool count in `.github/notes/architecture.md` to "Fourteen" and added wiki-lint to the table. However, wiki-update (PR #56, issue #14) was already absent from the table — the correct count should have been "Fifteen" (14 existing + 1 new). Only 1 of 3 review models (Gemini) caught the count discrepancy; Claude incorrectly assessed the count as accurate.

### Observation

This is the **seventh** occurrence of the stale-count pattern (issues #4, #5, #11, #12, #30, #13, #17) but introduces a new failure mode: **compounding**. Previous occurrences were simple count inaccuracies — the Coder or Documenter updated the count to the wrong number. This time, the Documenter got the count wrong because a *prior entry was missing from the table entirely*. The Documenter added its new entry and counted the table rows, but the table was already incomplete.

The Documenter's verification checklist (Step 3) already covers directory trees ("re-run `ls` or `find` on the actual directory"), file paths, output formats, and file extensions. But it does not cover **inventory table completeness** — verifying that all items that should be in a table actually are, not just that the count label matches the row count.

The root cause is that the Documenter trusts the existing table content as a baseline and only adds/modifies entries for the current task. It does not cross-check the table against the actual files on disk to detect pre-existing gaps.

### Suggested Improvement

Add a verification bullet to the Documenter's Step 3 verification checklist (`.github/agents/documenter.agent.md`):

```markdown
> - For inventory tables (tools, collections, agents, categories): cross-check table entries against the actual source of truth on disk (e.g., `ls .opencode/tools/` for tool tables, `ls src/tools/` for script tables). Verify both that every row has a matching file AND that every file has a matching row — pre-existing missing entries compound with new additions to produce wrong counts.
```

This is a clarification — adding a missing verification example to the existing checklist, same pattern as the existing directory tree and file extension bullets.

### Action Taken

Applied: added inventory table verification bullet to the Documenter's Step 3 verification checklist.
