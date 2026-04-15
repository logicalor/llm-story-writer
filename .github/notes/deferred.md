# Deferred Ideas

Ideas and improvements that came up during development but were intentionally deferred.

---

## Create `scripts/git-safe-publish.sh`

**Date:** 2026-04-12
**Source:** Reflection — issue #1

The Orchestrator agent references `bash scripts/git-safe-publish.sh` in Steps 5d, 7, and 8 for staging, committing, pushing, and looping until the working tree is clean. The script does not exist yet. It is planned as part of the migration task sequence. Until it is created, agents must use manual `git add -A && git commit -m "..." && git push origin {branch}` commands.

---

## Create `scripts/verify-green.sh`

**Date:** 2026-04-12
**Source:** Reflection — issue #1

The Orchestrator references `bash scripts/verify-green.sh` in Step 7 for post-fix test verification. The script does not exist yet. Until created, agents should run `pytest tests/ -v` directly.

---

## Install pre-commit hooks

**Date:** 2026-04-12
**Source:** Reflection — issue #1

`.github/scripts/install-hooks.sh` and `pre-commit-hook.sh` exist but are not installed in the local repository. The `local-workflow.md` shared rules require pre-commit hooks to always run. Until hooks are installed, `git commit --no-verify` prohibitions are moot (there is nothing to verify). Installation should be part of an early migration task.

---

## Install ruff in project environment

**Date:** 2026-04-12
**Source:** Reflection — issue #1

`copilot-instructions.md` specifies `ruff check --fix .` and `ruff format .` as the project's lint/format commands. `ruff` is not currently installed in the Python environment. The Orchestrator's Step 5c will fail until ruff is available. Should be resolved as part of the development environment setup migration task.

---

## Investigate hanging test in `pytest tests/`

**Date:** 2026-04-15
**Source:** Reflection — issue #18

Running `pytest tests/` hangs after ~176 tests; `pytest tests/unit/` completes cleanly (241 passed). The hang is likely caused by root-level `test_*.py` files that attempt network calls or wait for input. Investigate and either fix (add timeouts/mocks) or exclude from default collection (add to `pyproject.toml` `testpaths` or a `conftest.py` `collect_ignore`).
