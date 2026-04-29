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

## Variant agent files diverge from parent permissions silently

### Finding

During the PR #253 permission-format migration sweep across all 24 `.opencode/agents/*.md` files, six variant files (`auditor-kimi.md`, `auditor-qwen.md`, `auditor-glm.md`, `researcher-kimi.md`, `researcher-qwen.md`, `researcher-glm.md`) were found missing permissions that their parent agents carry: `"chroma/*": true` and `"echo*": "allow"`. The divergence predates PR #253 but was not corrected during the sweep. The parent-to-variant diff was only surfaced by one model's programmatic check (S-C-01), subsequently confirmed by filesystem verification during synthesis. Issue #254 was opened to track the repair.

### Observation

The Coder has no guidance to verify variant file parity when editing a parent agent's permissions. Variant files are model-specific copies of parent agents and should share identical permissions unless intentionally diverged. Silent divergence causes variant-model agents to have reduced capabilities (no ChromaDB access, no echo commands) without any error or warning at runtime. This pattern will recur on any future permission change to `auditor.md` or `researcher.md` unless the Coder is instructed to check variants.

### Suggested Improvement

Add a sub-bullet to Coder Rule 10 requiring a parity check against all variant files when editing a parent agent's permission block. Enumerate the known variant families so the Coder can grep for the pattern without having to infer it.

### Action Taken

Applied: Added sub-bullet to `.opencode/agents/coder.md` Rule 10 specifying the variant file parity check requirement, enumerating the auditor and researcher variant families.
