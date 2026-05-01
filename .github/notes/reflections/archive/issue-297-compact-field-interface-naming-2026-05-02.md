---
date: "2026-05-02"
issue: 297
pr: 309
category: instruction
targets:
  - ".github/notes/gotchas.md"
severity: minor
---

## Short-circuit output field named for interface slot, not content description

### Finding

During issue #297 (PR #309, RecapWriterAgent), the compact-path short-circuit was
implemented as: when `use_multi_stage_recap_sanitizer=False`, place the `format_json`
output directly into the `compact` field and return early — skipping all sanitizer stages.
The field is named `compact` even though its content is not actually compacted (it is the
full format-stage output). The name was chosen for interface consistency: callers always
read `data.compact`, regardless of which path was taken.

### Observation

Short-circuit paths in multi-stage pipelines must satisfy the same interface contract as
the full path. When a caller expects `data.compact`, both the full path (sanitizer output)
and the short-circuit path (format_json directly) must write to `data.compact`. Naming the
short-circuit output field after its *content* (e.g., `data.format_output`) instead of the
*interface slot* (`data.compact`) would break all callers silently.

The pattern generalises: whenever a pipeline stage is optional and a short-circuit exists,
the short-circuit assigns the last available intermediate result to the same output field
that the full path assigns its final result to.

### Suggested Improvement

Add a gotcha entry (gotcha #042) to `.github/notes/gotchas.md` documenting the interface-
slot naming rule for short-circuit output fields in optional pipeline stages.

### Action Taken

Applied:
- Added gotcha #042 (short-circuit output field named for interface slot) to
  `.github/notes/gotchas.md`.
