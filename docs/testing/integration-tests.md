# Integration Tests

> How to run the live end-to-end integration suite for the full story generation pipeline with wiki support.

## Overview

The integration suite verifies the full OpenCode-compatible story pipeline against a real LLM endpoint. It exercises story state initialisation, wiki setup, outline generation, character and setting sheet generation, wiki population, scene writing, recap generation, wiki linting, savepoint creation, and final story assembly.

These tests are intentionally heavier than unit tests. They make live model calls, create temporary story and ChromaDB directories, and validate that the pipeline works end to end instead of mocking tool boundaries.

## Scope

The suite currently lives in `tests/integration/` and includes:

- `tests/integration/conftest.py` — registers the `integration` pytest marker and provides the session-scoped `llm_available` fixture.
- `tests/integration/test_e2e_opencode.py` — a 12-test class that runs the full wiki-enabled generation pipeline and asserts the expected outputs at each stage.

The `llm_available` fixture checks `GET {LLM_API_BASE}/models` before the suite starts. If the endpoint is unreachable or returns a non-200 status, pytest skips the integration tests instead of failing them.

## Running The Suite

Run only unit tests:

```bash
pytest
```

Run the integration suite explicitly:

```bash
pytest tests/integration/ -v -m integration
```

Run the single end-to-end file with a longer timeout:

```bash
pytest tests/integration/test_e2e_opencode.py -v -m integration --timeout=7200
```

Run both unit and integration tests together:

```bash
pytest tests/unit tests/integration -v
```

## LLM Endpoint Configuration

The integration suite requires a live OpenAI-compatible LLM API.

`LLM_API_BASE` controls which endpoint the tests call:

- Default: `http://localhost:11434/v1`
- Health check used by the fixture: `GET {LLM_API_BASE}/models`
- Expected shape: an OpenAI-compatible `/models` route and compatible text-generation responses used by the tool layer

Examples:

```bash
# Default local Ollama-compatible endpoint
pytest tests/integration/ -v -m integration

# Custom host or port
LLM_API_BASE=http://192.168.1.50:11434/v1 pytest tests/integration/ -v -m integration

# LM Studio or another OpenAI-compatible server
LLM_API_BASE=http://127.0.0.1:1234/v1 pytest tests/integration/test_e2e_opencode.py -v -m integration --timeout=7200
```

If `LLM_API_BASE` is unset, the suite falls back to the local default. If the endpoint is down, pytest reports the suite as skipped.

## Duration And Runtime Expectations

Expect a full run to take roughly 30 to 90 minutes, depending on model speed, hardware, and endpoint latency.

Factors that most affect runtime:

- model size and tokens-per-second throughput
- network latency if the LLM runs on another host
- recap, outline, and scene generation latency across the 3-chapter, 2-scenes-per-chapter fixture story
- wiki snapshot and lint work after each generated scene

Use the longer timeout command when running the complete file or in CI-like environments with slower local inference.

## What The Suite Verifies

The 12 assertions cover these pipeline checkpoints:

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

## Manual Verification

After a successful run, inspect the temporary story path printed at the start of the test session (`Integration story dir: ...`). Review these outputs manually when you need extra confidence beyond pytest assertions:

- `stories/<temp>/e2e-test-story/wiki/index.md` — wiki page inventory
- `stories/<temp>/e2e-test-story/wiki/log.md` — wiki operation log
- `stories/<temp>/e2e-test-story/wiki/characters/*.md` — generated character pages
- `stories/<temp>/e2e-test-story/wiki/locations/*.md` — generated location pages
- `stories/<temp>/e2e-test-story/chapters/chapter_*.md` — assembled chapter content
- `stories/<temp>/e2e-test-story/savepoints/` — intermediate savepoints across the pipeline

Manual checks worth doing:

- confirm all expected wiki page types were created
- confirm character and location pages have valid frontmatter and non-empty bodies
- confirm chapter files exist for all 3 chapters and contain scene content
- confirm savepoints exist for outline, chapter, and recap-related steps
- confirm no obvious continuity break appears between generated chapters and wiki state

## Notes

The pytest configuration keeps default discovery focused on `tests/unit`. That keeps `pytest` fast for normal development, while integration runs stay explicit and opt-in.

Related: [Documentation Index](../README.md), [Tools Reference](../tools.md), [Story Orchestrator](../features/story-orchestrator.md)
