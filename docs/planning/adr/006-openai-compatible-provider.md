# ADR 006 — Replace Ollama SDK with Generic OpenAI-Compatible REST Provider

**Date:** 2026-04-17  
**Status:** Accepted  
**Context:** The production provider layer used the proprietary `ollama` Python SDK (v0.1.0+) which couples the system to Ollama-specific API endpoints (`/api/chat`, `/api/embeddings`, `/api/tags`) and response formats. Modern local inference servers (Ollama ≥ v0.1.24, LM Studio, vLLM, llama.cpp server, Koboldcpp) all expose an OpenAI-compatible REST API at `/v1/chat/completions` and `/v1/embeddings`.

**Decision:**  
Remove the `ollama` Python SDK. Replace `OllamaProvider` with `OpenAICompatibleProvider` that calls `/v1/chat/completions` via the `requests` library (mirroring the existing `LMStudioProvider`). Update `OllamaEmbeddingProvider` to call `/v1/embeddings` with the OpenAI payload format. Rename config key `ollama_host` → `model_api_base` accepting a full base URL. Keep `"ollama"` as a recognised URI scheme alias for backward compatibility.

**Consequences:**  
- Any OpenAI-compatible inference server can be used without code changes  
- `ollama` package removed from `requirements.txt`  
- `model_api_base` replaces `ollama_host` (old key still accepted as alias)  
- `ollama://` URI scheme still accepted; internally routes to `OpenAICompatibleProvider`  
- Model download via API is no longer supported (use native server tools)  
- Ollama-specific options (`think`, `keep_alive`, `num_ctx`) are dropped