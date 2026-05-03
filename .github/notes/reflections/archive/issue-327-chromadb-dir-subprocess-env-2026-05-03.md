---
date: "2026-05-03"
issue: 327
pr: 339
category: instruction
targets:
  - ".github/notes/gotchas.md"
  - ".github/agents/skills/test-verification/SKILL.md"
severity: minor
---

## Import-time env vars must be forwarded to subprocesses explicitly

### Finding

`CHROMADB_DIR` is read at module-level in `wiki_search.py`. Subprocess integration tests that
omit it from the `env` dict cause the subprocess to target the default `.chromadb` path,
polluting the project root and making the test non-reproducible.

### Observation

Any tool that reads env vars at import time (not lazily) requires those vars in every subprocess
`env` dict. Parent-process `monkeypatch` cannot reach subprocess module-level initialisation.
Pattern generalises to all `os.environ.get(...)` calls at module scope.

### Suggested Improvement

Add gotcha #051 to `gotchas.md`. Add assertion bullet to `test-verification/SKILL.md`.

### Action Taken

Applied: Added gotcha #051 to `.github/notes/gotchas.md`. Added assertion bullet to
`.github/agents/skills/test-verification/SKILL.md`.
