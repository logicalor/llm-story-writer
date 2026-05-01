---
date: "2026-04-30"
issue: 254
pr: 255
category: agent
targets:
  - ".opencode/agents/coder.md"
severity: minor
status: archived
---

> **Archived.** See canonical copy: `archive/issue-254-tools-ordering-coder-guidance-2026-04-30.md`


### Finding

The synthesized review for PR #253 (finding S-C-01 in the Claude report, later confirmed) identified a tools ordering inconsistency between the auditor variant files and their parent: the parent `auditor.md` lists `"chroma/*"` before `"io.github.tavily-ai/..."`, while the variants had `"chroma/*"` last. Issue #256 was opened to track the correction. The Coder's existing variant-parity rule (Rule 10 sub-bullet) instructs applying "the identical change" to variant files when editing a parent but does not mention preserving the parent's key ordering in the `tools:` block.

### Observation

Ordering inconsistencies in YAML `tools:` blocks do not affect runtime behaviour but they cause noisy diffs, confuse reviewers, and generate otherwise-avoidable follow-up issues. The variant-parity sub-bullet already addresses content parity; a brief note about ordering parity would close the gap without adding significant cognitive load.

### Suggested Improvement

Append a sentence to the existing variant-parity sub-bullet in coder.md Rule 10 noting that the parent agent's `tools:` key ordering should be preserved when adding entries to a variant file.

### Action Taken

Applied: Appended ordering note to the variant permission parity sub-bullet in `.opencode/agents/coder.md` Rule 10.
