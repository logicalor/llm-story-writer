# Integration Tests

> How to run the live integration suite for the story pipeline, including the headless batch E2E test and slow-test marker workflow.

## Overview

The integration suite verifies the story pipeline against a real OpenAI-compatible LLM endpoint. It exercises story state initialisation, wiki setup, outline generation, character and setting sheet generation, wiki population, scene writing, recap generation, wiki linting, savepoint creation, and final story assembly.

The integration area includes one end-to-end path and a focused live smoke test for `OpenAIAsyncProvider`. `test_end_to_end_headless.py` covers the headless Python CLI batch runner by invoking `python -m src.presentation.cli.main run --story e2e_test_ --batch` in a subprocess and asserting that savepoints and approved chapter outputs are created. `test_openai_async_provider_live.py` covers streaming behaviour against a live endpoint.

These tests are intentionally heavier than unit tests. They make live model calls, create temporary story and ChromaDB directories, and validate real runtime behaviour instead of mocking tool boundaries.

## Scope

The suite currently lives in `tests/integration/` and includes:

- `tests/integration/conftest.py` — registers the `integration` pytest marker and provides the session-scoped `llm_available` fixture.
- `tests/integration/test_end_to_end_headless.py` — a slow headless E2E test that creates `stories/e2e-test/state.json`, runs the Python CLI in batch mode, auto-skips when LM Studio is unavailable, and checks savepoints, `pipeline_state.json`, approved chapter count, chapter titles, chapter content, and a 600-second wall-clock budget.
- `tests/integration/test_openai_async_provider_live.py` — a live streaming smoke test for `OpenAIAsyncProvider` that asserts multiple streamed chunks are received from a real endpoint.

The `llm_available` fixture checks `GET {LLM_API_BASE}/models` before the end-to-end pipeline suite starts. If the endpoint is unreachable or returns a non-200 status, pytest skips that suite instead of failing it.

`test_end_to_end_headless.py` does not use `llm_available`. Its `require_lm_studio` fixture probes `http://127.0.0.1:1234/v1/models` directly with `httpx` and skips the test when LM Studio is not reachable there.

`test_openai_async_provider_live.py` does not use `llm_available`. It is a direct live probe of streaming behaviour and will fail if the endpoint is down or the selected model is unavailable.

## Running The Suite

Run only unit tests:

```bash
pytest
```

Run the integration suite explicitly:

```bash
pytest tests/integration/ -v -m integration
```

Run only slow integration coverage:

```bash
pytest tests/integration/ -v -m slow
```

Run the headless batch E2E test:

```bash
pytest tests/integration/test_end_to_end_headless.py -v -m "integration and slow"
```

Run only the async provider live test:

```bash
LLM_API_BASE=http://127.0.0.1:1234/v1 \
TEST_OPENAI_ASYNC_MODEL=local-model \
pytest tests/integration/test_openai_async_provider_live.py -v -m integration
```

Run the single end-to-end file with a longer timeout:

```bash
pytest tests/integration/test_end_to_end_headless.py -v -m "integration and slow" --timeout=7200
```

Run only the non-slow integration tests:

```bash
pytest tests/integration/ -v -m "integration and not slow"
```

Run both unit and integration tests together:

```bash
pytest tests/unit tests/integration -v
```

## Pytest Markers

Pytest uses two markers for live integration coverage:

- `@pytest.mark.integration` — marks tests that require a live LLM service and should not be treated like fast unit coverage.
- `@pytest.mark.slow` — marks tests that may take multiple minutes. This marker is registered in `pyproject.toml` under `[tool.pytest.ini_options]`.

Use marker expressions to control runtime:

- `pytest tests/integration/ -m integration` — all live integration tests
- `pytest tests/integration/ -m slow` — only slow tests
- `pytest tests/integration/ -m "integration and not slow"` — live tests except slow coverage

## LLM Endpoint Configuration

The integration suite requires a live OpenAI-compatible LLM API.

`LLM_API_BASE` controls which endpoint the tests call:

- Default: `http://127.0.0.1:1234/v1`
- Health check used by the fixture: `GET {LLM_API_BASE}/models`
- Expected shape: an OpenAI-compatible `/models` route and compatible text-generation responses used by the tool layer

The headless E2E file has one extra constraint:

- `tests/integration/test_end_to_end_headless.py` currently probes `http://127.0.0.1:1234/v1/models` directly through `LM_STUDIO_URL`
- Because of that hardcoded probe, run LM Studio there or expose a compatible endpoint on that exact address before invoking the test
- If the endpoint is absent, pytest skips the test instead of failing it

`TEST_OPENAI_ASYNC_MODEL` optionally selects the model used by `test_openai_async_provider_live.py`. If unset, that test falls back to `LLM_MODEL`, then `local-model`.

Examples:

```bash
# Default local LM Studio endpoint
pytest tests/integration/ -v -m integration

# Custom host or port
LLM_API_BASE=http://192.168.1.50:1234/v1 pytest tests/integration/ -v -m integration

# Headless batch E2E test against local LM Studio
pytest tests/integration/test_end_to_end_headless.py -v -m "integration and slow"

# Ollama or another OpenAI-compatible server
LLM_API_BASE=http://127.0.0.1:11434/v1 pytest tests/integration/test_openai_async_provider_live.py -v -m integration

# Async provider smoke test against a loaded model
LLM_API_BASE=http://127.0.0.1:1234/v1 TEST_OPENAI_ASYNC_MODEL=local-model \
	pytest tests/integration/test_openai_async_provider_live.py -v -m integration
```

If `LLM_API_BASE` is unset, the `llm_available`-based tests fall back to the local default. If the endpoint is down, pytest reports those tests as skipped. The headless LM Studio test also skips when its direct health probe fails.

## Duration And Runtime Expectations

Expect a full integration run to take roughly 30 to 90 minutes, depending on model speed, hardware, and endpoint latency.

The headless batch test sets a stricter budget: the subprocess run must finish within 600 seconds.

Factors that most affect runtime:

- model size and tokens-per-second throughput
- network latency if the LLM runs on another host
- recap, outline, and scene generation latency across the 3-chapter, 2-scenes-per-chapter fixture story
- wiki snapshot and lint work after each generated scene

Use the longer timeout command when running the complete file or in CI-like environments with slower local inference.

## What The Suite Verifies

Across the current integration files, coverage includes these checkpoints:

1. Story state initialises correctly.
2. Wiki directory structure and index files are created.
3. Outline generation produces story elements and chapter structure.
4. Character sheets exist for expected entities.
5. Setting sheets exist for expected locations.
6. Wiki is populated from outline and generated sheets.
7. Chapters and scenes are generated.
8. Wiki updates after scene generation.
9. Wiki lint reports no errors.
10. Savepoints exist for key pipeline stages.
11. Final story assembly output exists.
12. Wiki snapshot token budgets stay within limits.
13. Headless CLI batch mode exits with code 0.
14. `savepoints/pipeline_state.json` is written during the headless run.
15. At least two approved chapters are present with `Chapter` in the title and non-empty content.
16. Headless runtime stays within the 600-second budget.
17. Wiki artifacts (`wiki/index.md`, `wiki/log.md`, `wiki/timeline/`) exist after the headless run and `pipeline_state.json` contains `wiki_batches` with per-chapter `updated_pages` and `new_pages` entries.

## Manual Verification

After a successful run, inspect the temporary story path printed at the start of the test session (`Integration story dir: ...`). Review these outputs manually when you need extra confidence beyond pytest assertions:

- `stories/<temp>/e2e-test-story/wiki/index.md` — wiki page inventory
- `stories/<temp>/e2e-test-story/wiki/log.md` — wiki operation log
- `stories/<temp>/e2e-test-story/wiki/characters/*.md` — generated character pages
- `stories/<temp>/e2e-test-story/wiki/locations/*.md` — generated location pages
- `stories/<temp>/e2e-test-story/chapters/chapter_*.md` — approved chapter files written during the per-chapter loop
- `stories/<temp>/e2e-test-story/output/story.md` — final manuscript assembled from approved chapters
- `stories/<temp>/e2e-test-story/savepoints/` — intermediate savepoints across the pipeline

Manual checks worth doing:

- confirm all expected wiki page types were created
- confirm character and location pages have valid frontmatter and non-empty bodies
- confirm chapter files exist for all 3 chapters and contain scene content
- confirm `output/story.md` exists and contains the assembled manuscript text
- confirm savepoints exist for outline, chapter, and recap-related steps
- confirm no obvious continuity break appears between generated chapters and wiki state

## Notes

The pytest configuration keeps default discovery focused on `tests/unit`. That keeps `pytest` fast for normal development, while integration runs stay explicit and opt-in through `tests/integration/` and marker selection.

Related: [Documentation Index](../README.md), [Tools Reference](../tools.md), [Story Orchestrator](../features/story-orchestrator.md)
