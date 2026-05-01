---
date: "2026-05-02"
issue: 298
pr: 310
category: instruction
targets:
  - ".github/notes/gotchas.md"
severity: minor
---

## Pre-existing `tools._io` double-import mypy error masks CI type-check signal

### Finding

During issue #298 (PR #310), running `mypy src/` fails with a pre-existing error: `tools._io` is imported twice from different roots (`src/tools/_io.py` and `tools/_io.py` resolve to the same module, causing a "Duplicate module named '_io'" error). This error is unrelated to the PR's changes but appears in the `mypy` output for every type-check run on this branch and future branches, making it harder to identify PR-introduced type errors.

### Observation

The pre-existing mypy failure is a known noise source. Without an explicit record, contributors who run `mypy src/` and see the failure may either:
- Attribute it to their PR and waste time investigating a false alarm
- Dismiss all mypy output as unreliable (higher risk: genuine errors may be ignored)

The correct behaviour is to note the pre-existing baseline, skip the known error when verifying type safety, and focus only on new errors introduced by the PR.

### Suggested Improvement

Add gotcha #044 to `gotchas.md` documenting the `tools._io` double-import as a known pre-existing mypy baseline error. Include a workaround: run `mypy src/ 2>&1 | grep -v "_io"` to filter the known error when checking for PR-introduced regressions. Also note that this error should be resolved by consolidating the dual import roots (tracked separately).

### Action Taken

Applied: Added gotcha #044 to `.github/notes/gotchas.md`.
