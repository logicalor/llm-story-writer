---
date: "2026-04-26"
issue: 188
pr: 201
category: agent
targets:
  - ".github/agents/synthesizing-reviewer.agent.md"
severity: minor
status: active
---

## Test coverage claims rejected by class-name search may be disproved by filename-pattern search

### Finding

GPT raised S-W-02 (downgraded to non-blocking in synthesis) asserting that `rag_integration_service.py` had no removal regression tests — contradicting ADR 008's claim of "removal regression tests." GPT's verification searched for `rag_integration_service`, `RAGIntegrationService`, `content_chunker`, and `ContentChunker` across `tests/`. The search returned zero matches and the finding was accepted.

The actual file `tests/unit/test_rag_service_removal.py` exists on disk and contains ten targeted removal tests (confirmed in `.pytest_cache/v/cache/nodeids`). The file was added in PR #102. GPT's search strategy was class-name centric — it searched for the service's class and module names but not for test files named after the deletion pattern (`test_*_removal.py`, `test_*_guard.py`). The synthesizer accepted the finding without cross-checking by filename.

### Observation

Two orthogonal search strategies exist for verifying test coverage for a service being removed:

1. **Class/module name search** — `grep -r "ServiceClassName\|module_name" tests/` — finds tests that import or explicitly reference the service. Returns zero matches for tests that verify the service was _removed_ from its consumers' constructor signatures (removal regression tests do not import the deleted class).
2. **Filename pattern search** — `ls tests/unit/test_*removal* tests/unit/test_*guard*` or `find tests/ -name 'test_*rag*'` — finds test files created specifically to guard against regression after a deletion.

When a reviewer claims "no tests exist for X" based only on strategy 1 (class/module name search), that claim is not disproved by strategy 2 returning no results — but it also is not _validated_ until strategy 2 has been tried. The synthesizer should require both search strategies before accepting a "no tests exist" finding as valid.

This is the converse of the existing "companion file not updated" filter (issue #185): rather than verifying that a file claimed to need updating was actually not updated, here the synthesizer must verify that a file claimed to be missing actually does not exist at any expected location.

### Suggested Improvement

Add a new false-positive filter to `synthesizing-reviewer.agent.md` Step 2, immediately after the "Out-of-diff violation claims filter":

> **"No tests exist for X" coverage claims filter:** If a reviewer asserts that no test coverage exists for a service, module, or feature — typically based on a class-name or module-name `grep` across `tests/` — verify the claim with a complementary filename-pattern search before accepting it. Run `find tests/ -name 'test_*<keyword>*'` where `<keyword>` is the domain term or snake_case service name. Removal regression tests (files that verify a service was cleanly excised from all callers) are named after the deletion operation — e.g., `test_rag_service_removal.py`, `test_outline_generator_rag_guard.py` — and will not contain the deleted class's name anywhere in their source. A "no tests exist" finding based solely on class-name search is `[unverified]` until a filename-pattern search also returns zero results. (Source: issue #188, PR #201 — GPT raised Warning that rag_integration_service.py had no removal tests; test_rag_service_removal.py exists with 10 removal tests and was missed because it imports no RAG class names.)

### Action Taken

Applied: added "No tests exist for X" coverage claims filter to `synthesizing-reviewer.agent.md` Step 2, after the Out-of-diff violation claims filter.
