# Deferred Ideas

Ideas and improvements that came up during development but were intentionally deferred.

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
---

## Fix pre-existing test failures in `test_story_state_tool.py` and `test_wiki_extract_tool.py`

**Date:** 2026-04-24
**Source:** Reflection — issue #160, PR #170

19 pre-existing failures were observed in `tests/unit/test_story_state_tool.py` and `tests/unit/test_wiki_extract_tool.py` on the development branch. These failures pre-date PR #170 and are unrelated to the pipeline primitives implementation. Likely caused by stale mocks, missing fixtures, or API changes not back-propagated to these test files.

These create noise in PR baselines — reviewers must manually filter them out each time, which is error-prone. Should be resolved in a dedicated cleanup issue. File a GitHub issue and address in the next available sprint slot.