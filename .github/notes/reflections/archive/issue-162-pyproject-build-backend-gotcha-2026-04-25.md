---
date: "2026-04-25"
issue: 162
pr: 172
category: instruction
targets:
  - ".github/notes/gotchas.md"
severity: minor
status: archived
---

## Invalid `setuptools.backends.legacy:build` in pyproject.toml `[build-system]`

### Finding

During PR #172 (CLI entry points wiring), the Coder wrote the `[build-system]` table in
`pyproject.toml` with `build-backend = "setuptools.backends.legacy:build"`. This is not a valid
PEP 517 backend string — the correct value is `setuptools.build_meta`. All three review models
(Claude, GPT, Gemini) flagged this independently as a Critical finding before merge.

The invalid string does not fail at `pyproject.toml` parse time; it fails only at
`pip install` or `python -m build` invocation with a confusing `ModuleNotFoundError` or
`BackendUnavailable` that does not identify the pyproject table as the cause.

### Observation

The string `setuptools.backends.legacy:build` is a plausible-looking fabrication — it
resembles the format used by Flit (`flit_core.buildapi`) and Poetry (`poetry.core.masonry.api`)
which use `module:callable` notation. Setuptools however exports its backend at the flat path
`setuptools.build_meta`. The pattern is easy to fabricate incorrectly when writing pyproject.toml
from memory.

Because the failure is deferred to install time (not parse time), it would not be caught by
lint or type checks that run only on source files. The only signals are a three-model review
consensus and an attempt to install the package.

### Suggested Improvement

Add gotcha entry #020 to `.github/notes/gotchas.md` under a new `## CLI / Entry Points` section
documenting the correct backend string and the deferred-failure risk.

### Action Taken

Applied: added gotcha entry #020 (`gotcha-pyproject-build-backend-020`) to
`.github/notes/gotchas.md` under `## CLI / Entry Points`.
