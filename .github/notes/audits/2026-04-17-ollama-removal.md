## Targeted Audit: Ollama-Specific Code Removal — 2026-04-17

**Audit Type:** Direct single-pass (Synthesizing Auditor — sequential tool search)
**Scope:** All Ollama SDK and Ollama-specific API code remaining in production `src/` layer
**Trigger:** Readiness audit 2026-04-16 identified surviving Ollama references; refactor goal is to replace with generic OpenAI-compatible REST calls

---

## Executive Summary

The Ollama refactor is **incomplete**. The production `src/` layer still contains a full `OllamaProvider` implementation that uses the `ollama` Python SDK (not generic REST), an `OllamaEmbeddingProvider` that calls Ollama-proprietary endpoints, and pervasive `ollama_host` config wiring throughout the container and config system. Ten production files require changes; the `ollama` package must be removed from `requirements.txt`. The `LMStudioProvider` already demonstrates the correct OpenAI-compatible HTTP pattern and should serve as the template for the replacement.

---

## Finding Inventory

### Critical Findings — Production Code

```
[C-01] OllamaProvider uses Ollama Python SDK (not REST)
File: src/infrastructure/providers/ollama_provider.py
Lines: 27–35, 519, 522
Detail: The provider imports the `ollama` Python package and calls `ollama.Client(host=host)`.
  This SDK communicates with the Ollama-native API (`/api/generate`, `/api/chat`) rather than
  the OpenAI-compatible endpoints (`/v1/chat/completions`). The constructor calls
  `_ensure_ollama_installed()`, which even auto-installs the `ollama` pip package if missing.
  This is the primary target for replacement: the class must be rewritten to use `httpx` or
  the `openai` Python SDK with a configurable `base_url` pointing to the inference server's
  `/v1/` endpoint (which Ollama, LM Studio, llama.cpp, and any other OpenAI-compatible server
  all expose).
Impact: Tight dependency on Ollama. Cannot route requests to non-Ollama OpenAI-compatible
  servers (e.g., vLLM, Koboldcpp, OpenRouter direct) through this code path.
Recommended action: Replace with `OpenAICompatibleProvider` using `openai` SDK or `httpx`.
  Pattern already demonstrated by `LMStudioProvider` (requests-based OpenAI-compatible calls).
```

```
[C-02] OllamaEmbeddingProvider calls Ollama-proprietary endpoints
File: src/infrastructure/providers/ollama_embedding_provider.py
Lines: 41–65
Detail: The `_get_single_embedding()` method POSTs to `/api/embeddings` with payload
  `{"model": ..., "prompt": ...}`. The `test_connection()` method GETs `/api/tags`. Both
  are Ollama-proprietary endpoints. The OpenAI-compatible embedding endpoint is
  `/v1/embeddings` with payload `{"model": ..., "input": ...}`, which Ollama also exposes
  since Ollama v0.1.24. This file should be updated to use the OpenAI-compatible endpoint.
Impact: Embedding provider will break against any non-Ollama inference server.
Recommended action: Change POST URL to `/v1/embeddings`; change payload key from
  `"prompt"` to `"input"`; change connection-test URL to `/v1/models` or `/`.
```

```
[C-03] Container hardwires OllamaProvider as default model provider
File: src/infrastructure/container.py
Lines: 9, 37–39, 93, 102, 124–125
Detail: The container imports `OllamaProvider` and registers it as the singleton
  `ollama_provider`. Both `strategy` and `story_generation_service` singletons are wired to
  `model_provider=ollama_provider` — making Ollama the unconditional default for all story
  generation. `get_model_provider("ollama")` returns this instance. When the provider is
  renamed/replaced, these wiring points must all change to the new provider class and name.
Impact: Every story generation call goes through the Ollama SDK path regardless of config.
Recommended action: Replace `OllamaProvider` import and all wiring with
  `OpenAICompatibleProvider`. Update default provider string from `"ollama"` to
  `"openai_compatible"` (or equivalent agreed name).
```

```
[C-04] ollama_host config key hardcoded throughout config system
Files: src/config/config_loader.py (lines 51–52), src/config/rag_config.py (lines 34–61, 83)
Detail: `config_loader.py` reads `ollama_host` from the config file and defaults to
  `"127.0.0.1:11434"`. `rag_config.py` exposes an `ollama_host` property that parses the
  `ollama://` URL scheme. The default embedding model is also `"ollama://nomic-embed-text"`.
  These are Ollama-specific assumptions that should become provider-agnostic.
Impact: Config schema is Ollama-specific; new generic provider cannot be configured cleanly.
Recommended action: Rename `ollama_host` → `model_api_base` (or `inference_host`) in both
  the config schema and the loader. Update `rag_config.py` to parse a generic `openai://`
  or `http://` URL scheme rather than `ollama://`. Update default embedding model string
  to reflect the new scheme (e.g., `openai-compat://nomic-embed-text`).
```

```
[C-05] LangChainProvider has Ollama-specific branch
File: src/infrastructure/providers/langchain_provider.py
Lines: 650–654
Detail: The `_create_langchain_llm()` method has `elif provider == "ollama":` which imports
  `langchain_community.llms.Ollama` and creates an Ollama LangChain LLM. This is a
  LangChain-native Ollama integration (not OpenAI-compatible). The correct replacement is
  `ChatOpenAI(model=model_name, base_url=f"http://{host}/v1", openai_api_key="ollama", ...)`.
Impact: LangChain path for Ollama models bypasses the OpenAI-compatible API.
Recommended action: Replace the `elif provider == "ollama":` branch with a branch that
  creates `ChatOpenAI` with `base_url` set to the host's `/v1/` endpoint.
```

```
[C-06] ModelConfig domain object lists "ollama" as a valid provider
File: src/domain/value_objects/model_config.py
Lines: 28, 54, 64–65
Detail: The `valid_providers` set contains `"ollama"`. The `from_string()` method defaults
  bare model names (no `://`) to `provider="ollama"`. There is Ollama-specific URL parsing
  logic in the `elif provider == "ollama":` branch. All three points tie the domain model
  to Ollama.
Impact: Domain validation allows `"ollama"` provider strings; removing Ollama without
  updating this will either break existing configs or require an alias.
Recommended action: Decide on the canonical provider name for OpenAI-compatible servers
  (e.g., `"openai_compatible"` or keep `"ollama"` as an alias). Update `valid_providers`,
  the default fallback, and the URL parsing branch accordingly. If `"ollama"` is kept as
  an alias, document it explicitly.
```

```
[C-07] RAGService imports OllamaEmbeddingProvider directly
File: src/application/services/rag_service.py
Lines: 12, 40
Detail: `rag_service.py` imports `OllamaEmbeddingProvider` and uses it in the constructor
  type signature, even though the class carries a deprecation warning. This import will
  break when `OllamaEmbeddingProvider` is removed or renamed.
Impact: Import failure when Ollama classes are removed.
Recommended action: Update the import and type annotation to use the new embedding provider
  name. Since the service is deprecated, the simplest fix is updating the import to the
  new class name without other changes.
```

```
[C-08] ollama package in requirements.txt
File: requirements.txt
Line: 2
Detail: `ollama>=0.1.0` is listed as a core dependency. This is the Ollama Python SDK
  that should be removed once OllamaProvider is replaced with an HTTP-based provider.
Impact: Unnecessary dependency; installs the Ollama SDK even when not needed.
Recommended action: Remove `ollama>=0.1.0`. Add `httpx>=0.27.0` (async HTTP) and/or
  confirm `openai>=1.0.0` is available (it is transitively via langchain-openai) for the
  new provider implementation.
```

```
[C-09] providers/__init__.py exports OllamaProvider
File: src/infrastructure/providers/__init__.py
Lines: 2, 8
Detail: The package `__init__.py` publicly exports `OllamaProvider`. Any code importing
  from this package gets Ollama. When the class is renamed/replaced, this export list
  must be updated.
Impact: Public API of the providers package still named after Ollama.
Recommended action: Replace `OllamaProvider` export with `OpenAICompatibleProvider`
  (or equivalent). If a backward-compat alias is needed, add one explicitly.
```

### Warning Findings — Root-Level Test Files

These files live at the repo root (outside `tests/`) and appear to be legacy integration
tests. They are not part of the canonical `pytest` test suite under `tests/` but will
fail with import errors once `OllamaProvider` is removed.

```
[W-01] test_multistep_conversation.py imports OllamaProvider
File: test_multistep_conversation.py
Lines: 12, 27, 124, 215, 333
Detail: Imports `OllamaProvider` and instantiates it with `host="127.0.0.1:11434"` in
  four places.
Recommended action: Update to import and use the new provider class.
```

```
[W-02] test_character_sheet_generation.py imports OllamaProvider; hardcodes provider="ollama"
File: test_character_sheet_generation.py
Lines: 15, 26–38, 54, 157
Detail: Imports `OllamaProvider` and sets `provider="ollama"` for all 12 model role
  configs. Hardcoded strings will need to change to the new provider name.
Recommended action: Update import and all `provider="ollama"` strings to the new name.
```

```
[W-03] test_chapter_synopsis_generation.py imports OllamaProvider
File: test_chapter_synopsis_generation.py
Lines: 15, 31
Detail: Imports `OllamaProvider` and instantiates with `config.ollama_host`.
Recommended action: Update import, instantiation, and config key reference.
```

```
[W-04] test_progressive_story_generation.py imports OllamaProvider
File: test_progressive_story_generation.py
Lines: 14, 42
Detail: Imports `OllamaProvider`.
Recommended action: Update import.
```

### Warning Findings — Canonical Test Suite

```
[W-05] tests/unit/test_model_config.py tests Ollama-specific provider string behaviour
File: tests/unit/test_model_config.py
Lines: 11–97
Detail: Multiple tests assert `config.provider == "ollama"` and use `"ollama://"` URL
  strings and validate `"ollama"` as the default provider for bare model names. These
  tests are correct for current behaviour but will require update when the provider
  name and/or default change.
Recommended action: Update expected provider names and URL schemes to match the new
  generic provider. Keep test coverage of URL parsing; just update the expected values.
```

### Warning Findings — Config files (Active)

```
[W-06] config.md uses ollama:// URI scheme and ollama_host key
File: config.md
Lines: 7–24, 63, 73, 161, 180–197
Detail: This is the active runtime config file. All model role URIs use `ollama://` scheme
  and `ollama_host` is documented as a config key. Users reading this file will be
  confused after the refactor.
Recommended action: Update after the code changes. Change URL scheme examples to the new
  generic scheme. Rename `ollama_host` → the new config key. Add a note explaining that
  the inference server must expose OpenAI-compatible endpoints.
```

```
[W-07] config.example.sh, configs/fast-prototype.sh, configs/high-quality.sh use ollama:// URIs
Files: config.example.sh, configs/fast-prototype.sh, configs/high-quality.sh
Detail: All example config files hardcode `ollama://` URI scheme for every model role.
Recommended action: Update example values to use the new URL scheme.
```

### Informational Findings

```
[I-01] rag_query_cli.py imports OllamaProvider and OllamaEmbeddingProvider
File: rag_query_cli.py
Lines: 125, 143, 173, 177, 230, 246, 552, 615, 627, 665, 840, 850
Detail: This root-level CLI script imports and uses both `OllamaProvider` (for story query
  AI responses) and `OllamaEmbeddingProvider` (via config.ollama_host) extensively.
Recommended action: Update imports and config key references when providers are replaced.
```

```
[I-02] migrate_embed.py uses config.ollama_host
File: migrate_embed.py
Line: 47
Detail: Instantiates `OllamaEmbeddingProvider` via `config.ollama_host`. Will break when
  config key is renamed.
Recommended action: Update config key reference.
```

```
[I-03] migrate_embed.sh hardcodes ollama:// URI examples
File: migrate_embed.sh
Lines: 29, 63, 96, 99, 104
Detail: Shell script examples use `ollama://` URI scheme.
Recommended action: Update examples after code changes.
```

```
[I-04] setup_rag.sh requires Ollama to be running
File: setup_rag.sh
Lines: 16–40
Detail: Setup script checks for and starts Ollama, then calls `ollama pull` to download
  embedding models. If the inference server is changed to a non-Ollama provider, this
  script will need updating.
Recommended action: Generalise or replace after the broader provider refactor.
```

```
[I-05] opencode.json uses ollama/ model references
File: opencode.json
Lines: 4, 6, 28, 49, 54, 59, 64
Detail: The OpenCode tool configuration uses `ollama/...` model strings for the agent
  orchestration layer. This is a *separate concern* from the Python application provider
  system — it controls which model OpenCode routes requests to, not which provider class
  is used in Python. This MAY be intentional (OpenCode speaks directly to Ollama via its
  own routing), but should be reviewed once the broader refactor is complete to confirm
  the model routing strategy.
Recommended action: Review separately; do not change as part of the Python provider refactor.
```

```
[I-06] ADR 003 still references Ollama for embeddings without noting the refactor goal
File: docs/planning/adr/003-chromadb-replaces-pgvector.md
Lines: 24, 39, 53
Detail: ADR 003 was written assuming Ollama remains for embedding. No ADR documents the
  decision to remove the Ollama SDK entirely and replace with OpenAI-compatible calls.
Recommended action: Write a new ADR (006 or 007) documenting the decision to replace
  the Ollama SDK with a generic OpenAI-compatible provider. ADR 003 may need an amendment
  noting that embedding calls will use the OpenAI-compatible `/v1/embeddings` endpoint.
```

---

## Summary Table

| ID    | File                                              | Severity | Type       |
| ----- | ------------------------------------------------- | -------- | ---------- |
| C-01  | src/infrastructure/providers/ollama_provider.py   | Critical | SDK usage  |
| C-02  | src/infrastructure/providers/ollama_embedding_provider.py | Critical | Endpoint   |
| C-03  | src/infrastructure/container.py                   | Critical | Wiring     |
| C-04  | src/config/config_loader.py + rag_config.py       | Critical | Config     |
| C-05  | src/infrastructure/providers/langchain_provider.py | Critical | SDK branch |
| C-06  | src/domain/value_objects/model_config.py          | Critical | Domain     |
| C-07  | src/application/services/rag_service.py           | Critical | Import     |
| C-08  | requirements.txt                                  | Critical | Dependency |
| C-09  | src/infrastructure/providers/__init__.py          | Critical | Export     |
| W-01  | test_multistep_conversation.py                    | Warning  | Test       |
| W-02  | test_character_sheet_generation.py                | Warning  | Test       |
| W-03  | test_chapter_synopsis_generation.py               | Warning  | Test       |
| W-04  | test_progressive_story_generation.py              | Warning  | Test       |
| W-05  | tests/unit/test_model_config.py                   | Warning  | Test       |
| W-06  | config.md                                        | Warning  | Config doc |
| W-07  | config.example.sh, configs/*.sh                  | Warning  | Config doc |
| I-01  | rag_query_cli.py                                 | Info     | CLI        |
| I-02  | migrate_embed.py                                 | Info     | Utility    |
| I-03  | migrate_embed.sh                                 | Info     | Utility    |
| I-04  | setup_rag.sh                                     | Info     | Setup      |
| I-05  | opencode.json                                    | Info     | Separate   |
| I-06  | docs/planning/adr/                              | Info     | Docs       |

---

## Migration Guidance

### Recommended approach

1. **New class: `OpenAICompatibleProvider`** — replaces `OllamaProvider`. Takes `base_url`
   (full URL e.g. `http://127.0.0.1:11434/v1`) instead of `host`. Uses the `openai` Python
   SDK with `OpenAI(base_url=..., api_key="none")` — the `openai` package is already
   transitively available via `langchain-openai`. This is the same pattern LM Studio and
   vLLM already use.

2. **Update `OllamaEmbeddingProvider`** — change POST URL from `/api/embeddings` to
   `/v1/embeddings`; change `"prompt"` key to `"input"`; change `test_connection()` URL
   from `/api/tags` to `/v1/models`. Rename class to `OpenAICompatibleEmbeddingProvider`.

3. **Config key rename** — `ollama_host` → `model_api_base` (or `inference_host`). Update
   `config_loader.py`, `rag_config.py`, `container.py`.

4. **Provider name** — recommend keeping `"ollama"` as a recognised URL scheme alias
   (since it _is_ the Ollama server) but routing it through `OpenAICompatibleProvider`.
   Alternatively rename to `"openai_compat"`. Decide and update `model_config.py` and
   `container.py` consistently.

5. **Remove** `ollama>=0.1.0` from `requirements.txt`.

6. **`langchain_provider.py`** — replace Ollama branch with `ChatOpenAI(base_url=...,
   api_key="none")`.

7. **Update all test files** — root-level and `tests/unit/test_model_config.py`.

8. **Write ADR** documenting the Ollama SDK removal decision.

### Files to leave unchanged
- Everything under `legacy/` — frozen archive per AGENTS.md.
- `opencode.json` — separate concern; OpenCode's own model routing, not the Python provider.

---

## Recommended Task Order

```
1. [C-08] Remove ollama from requirements.txt (simplest, confirms removals)
2. [C-01] Implement OpenAICompatibleProvider (largest change — core pattern)
3. [C-02] Update OllamaEmbeddingProvider to /v1/embeddings (small change)
4. [C-09] Update providers/__init__.py exports
5. [C-03] Update container.py wiring to new provider
6. [C-04] Rename ollama_host → model_api_base in config_loader.py and rag_config.py
7. [C-06] Update model_config.py valid_providers and defaults
8. [C-05] Update langchain_provider.py Ollama branch
9. [C-07] Update rag_service.py import
10. [W-01–W-04] Update root-level test files
11. [W-05] Update tests/unit/test_model_config.py
12. [W-06–W-07] Update config docs and example configs
13. [I-01–I-04] Update CLI/utility scripts
14. [I-06] Write new ADR for Ollama SDK removal decision
```
