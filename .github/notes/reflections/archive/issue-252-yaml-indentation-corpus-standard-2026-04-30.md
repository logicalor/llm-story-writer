---
date: "2026-04-30"
issue: 252
pr: 253
category: agent
targets:
  - ".opencode/agents/coder.md"
severity: minor
status: archived
---

## YAML frontmatter indentation inconsistency in agent corpus

### Finding

After migrating all 24 `.opencode/agents/*.md` files to the documented object-map permission format (PR #253), three files were found with non-standard YAML indentation relative to the 21-file corpus standard: `orchestrator-v3.md` (bash_indent=8, task_indent=8, tools_indent=4), `coder.md` (bash_indent=6, tools_indent=3), and `sprint-runner.md` (bash_indent=6, task_indent=6, tools_indent=3). The corpus standard — used by 21 of 24 files — is 4-space indent for sub-keys inside `bash:`, `task:`, and `edit:` blocks, and 2-space indent for `tools:` sub-keys. All three non-standard files produce valid YAML; the inconsistency is style-only with no functional impact.

### Observation

The Coder agent has no guidance about YAML indentation style when editing `.opencode/agents/*.md` files. Three files with pre-existing non-standard indentation exist in the corpus and may be copied as incorrect references by future authors. The divergence was flagged by two of three synthesis review models (M-S-01) and produces noisy diffs and authoring confusion. The Coder is the primary author of new agent files, so this guidance belongs in its rule set.

### Suggested Improvement

Add a sub-bullet to Coder Rule 10 (under "New `.opencode/agents/*.md` files specifically") warning about the three non-standard reference files and specifying the corpus-standard indentation values. Advise using `auditor.md`, `researcher.md`, or `documenter.md` as indentation references.

### Action Taken

Applied: Added sub-bullet to `.opencode/agents/coder.md` Rule 10 specifying 4-space indent for bash/task/edit sub-keys and 2-space for tools sub-keys, with explicit warning not to copy from the three non-standard files (`orchestrator-v3.md`, `coder.md`, `sprint-runner.md`).
