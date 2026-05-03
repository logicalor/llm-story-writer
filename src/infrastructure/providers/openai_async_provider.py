"""Async OpenAI-compatible model provider implementation."""

import json
import os
import random
import re
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, Iterable, List, Optional, cast
from urllib.parse import urlparse, urlunparse

from openai import AsyncOpenAI, AsyncStream
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk

from application.interfaces.model_provider import ModelProvider
from domain.exceptions import ModelProviderError
from domain.value_objects.model_config import ModelConfig


def _append_debug_log(
    messages: List[Dict[str, str]],
    model: str,
    response: str,
) -> None:
    """Append one JSONL record to LLM_DEBUG_LOG if the env var is set."""
    log_path = os.environ.get("LLM_DEBUG_LOG")
    if not log_path:
        return
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "messages": messages,
        "response": response,
    }
    try:
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass  # Never let logging failures break generation


def _normalize_base_url(base_url: str) -> str:
    """Normalize model API base URL to include scheme and /v1 path."""
    candidate = base_url.strip()
    if not re.match(r"^https?://", candidate):
        candidate = f"http://{candidate}"

    parsed = urlparse(candidate)
    path = parsed.path.rstrip("/")
    if path in ("", "/"):
        path = "/v1"

    return urlunparse(
        (
            parsed.scheme or "http",
            parsed.netloc,
            path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    ).rstrip("/")


class OpenAIAsyncProvider(ModelProvider):
    """Async OpenAI-compatible model provider implementation."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 60.0,
        max_retries: int = 3,
        context_length: int = 16384,
        randomize_seed: bool = True,
    ):
        if base_url is None:
            base_url = os.environ.get("LLM_API_BASE", "http://127.0.0.1:1234/v1")

        resolved_api_key = api_key or os.environ.get("LLM_API_KEY") or "lm-studio"

        self.base_url = _normalize_base_url(base_url)
        self._api_key = resolved_api_key
        self._timeout = timeout
        self._max_retries = max_retries
        self.context_length = context_length
        self.randomize_seed = randomize_seed
        self._client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self._api_key,
            timeout=self._timeout,
            max_retries=self._max_retries,
        )
        self._clients: Dict[str, AsyncOpenAI] = {self.base_url: self._client}

    def _resolve_base_url(self, model_config: ModelConfig) -> str:
        """Resolve request base URL from model config override or provider default."""
        if model_config.host:
            return _normalize_base_url(model_config.host)
        return self.base_url

    def _get_client(self, model_config: ModelConfig) -> AsyncOpenAI:
        """Get async client for model config host override or default base URL."""
        base_url = self._resolve_base_url(model_config)
        client = self._clients.get(base_url)
        if client is None:
            client = AsyncOpenAI(
                base_url=base_url,
                api_key=self._api_key,
                timeout=self._timeout,
                max_retries=self._max_retries,
            )
            self._clients[base_url] = client
        return client

    def _filter_think_tags(self, text: str) -> str:
        """Remove <think>...</think> tags from text while preserving the rest."""
        filtered = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        filtered = re.sub(r"<think>.*", "", filtered, flags=re.DOTALL)
        filtered = re.sub(r"</think>.*", "", filtered, flags=re.DOTALL)
        return filtered

    def _prepare_options(
        self,
        model_config: ModelConfig,
        seed: Optional[int] = None,
        format_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Prepare options for OpenAI-compatible API call."""
        options = model_config.parameters.copy()

        if "max_tokens" not in options and "num_ctx" in options:
            options["max_tokens"] = options.pop("num_ctx")
        else:
            options.pop("num_ctx", None)

        options.pop("keep_alive", None)
        options.pop("think", None)
        options.pop("stream", None)

        max_tokens = options.get("max_tokens", self.context_length)
        if isinstance(max_tokens, (int, float)):
            max_tokens = int(max_tokens)
        else:
            max_tokens = self.context_length

        if max_tokens > self.context_length:
            print(
                f"[OPENAI ASYNC] Warning: Requested max_tokens {max_tokens} exceeds infrastructure limit {self.context_length}, capping to {self.context_length}"
            )
            max_tokens = self.context_length
        options["max_tokens"] = max_tokens

        if seed is not None:
            should_randomize = self.randomize_seed and not model_config.parameters.get(
                "static_seed", False
            )
            if should_randomize:
                random_offset = random.randint(1, 10000)
                options["seed"] = seed + random_offset
                print(
                    f"[OPENAI ASYNC] Seed randomized: {seed} + {random_offset} = {options['seed']}"
                )
            else:
                options["seed"] = seed
                print(f"[OPENAI ASYNC] Using static seed: {seed}")

        if format_type == "json":
            options["response_format"] = {"type": "json_object"}
            if "temperature" not in options:
                options["temperature"] = 0

        options.setdefault("temperature", 0.7)
        options.setdefault("top_p", 0.9)

        print(f"[OPENAI ASYNC] Context length: {options['max_tokens']}")
        return options

    async def generate_text(
        self,
        messages: List[Dict[str, str]],
        model_config: ModelConfig,
        seed: Optional[int] = None,
        format_type: Optional[str] = None,
        min_word_count: int = 1,
        debug: bool = False,
        stream: bool = False,
    ) -> str:
        """Generate text using async OpenAI-compatible API."""
        try:
            if debug:
                print(f"[OPENAI ASYNC] Model: {model_config.name}")
                print(f"[OPENAI ASYNC] Provider: {model_config.provider}")
                print(f"[OPENAI ASYNC] Stream: {stream}")

            if stream:
                chunks: List[str] = []
                async for chunk in self.stream_text(
                    messages=messages,
                    model_config=model_config,
                    seed=seed,
                    format_type=format_type,
                ):
                    print(chunk, end="", flush=True)
                    chunks.append(chunk)
                print()
                full_text = self._filter_think_tags("".join(chunks))
                _append_debug_log(messages, model_config.name, full_text)
                return full_text

            options = self._prepare_options(model_config, seed, format_type)
            response = await self._get_client(model_config).chat.completions.create(
                messages=cast(Iterable[ChatCompletionMessageParam], messages),
                model=model_config.name,
                stream=False,
                **options,
            )
            response = cast(ChatCompletion, response)
            response_text = response.choices[0].message.content or ""
            response_text = self._filter_think_tags(response_text)

            _append_debug_log(messages, model_config.name, response_text)

            if min_word_count > 1 and len(response_text.split()) < min_word_count:
                continued_messages = [
                    *messages,
                    {"role": "assistant", "content": response_text},
                    {
                        "role": "user",
                        "content": (
                            "Please continue and expand on this response to reach at "
                            f"least {min_word_count} words."
                        ),
                    },
                ]
                continuation = await self._get_client(
                    model_config
                ).chat.completions.create(
                    messages=cast(
                        Iterable[ChatCompletionMessageParam], continued_messages
                    ),
                    model=model_config.name,
                    stream=False,
                    **options,
                )
                continuation = cast(ChatCompletion, continuation)
                extra_text = continuation.choices[0].message.content or ""
                response_text = self._filter_think_tags(
                    f"{response_text}\n{extra_text}".strip()
                )

            return response_text
        except Exception as exc:
            raise ModelProviderError(f"OpenAI async generation failed: {exc}") from exc

    async def generate_multistep_conversation(
        self,
        user_messages: List[str],
        model_config: ModelConfig,
        system_message: Optional[str] = None,
        seed: Optional[int] = None,
        debug: bool = False,
        stream: bool = False,
    ) -> str:
        """Generate text through a multi-step conversation with memory."""
        messages: List[Dict[str, str]] = []
        if system_message:
            messages.append({"role": "system", "content": system_message})

        last_response = ""
        for user_message in user_messages:
            messages.append({"role": "user", "content": user_message})
            last_response = await self.generate_text(
                messages=messages,
                model_config=model_config,
                seed=seed,
                debug=debug,
                stream=stream,
            )
            messages.append({"role": "assistant", "content": last_response})

        return last_response

    async def generate_json(
        self,
        messages: List[Dict[str, str]],
        model_config: ModelConfig,
        required_attributes: List[str],
        seed: Optional[int] = None,
        debug: bool = False,
    ) -> Dict[str, Any]:
        """Generate JSON response using async OpenAI-compatible API."""
        try:
            response_text = await self.generate_text(
                messages=messages,
                model_config=model_config,
                seed=seed,
                format_type="json",
                debug=debug,
            )

            try:
                parsed = json.loads(response_text)
            except json.JSONDecodeError:
                json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
                if not json_match:
                    raise ModelProviderError("Failed to parse JSON response")
                try:
                    parsed = json.loads(json_match.group())
                except json.JSONDecodeError as exc:
                    raise ModelProviderError(
                        f"Failed to parse JSON response: {exc}"
                    ) from exc

            missing_attributes = [
                attr for attr in required_attributes if attr not in parsed
            ]
            if missing_attributes:
                raise ModelProviderError(
                    "JSON response missing required attributes: "
                    + ", ".join(missing_attributes)
                )

            return parsed
        except ModelProviderError:
            raise
        except Exception as exc:
            raise ModelProviderError(
                f"OpenAI async JSON generation failed: {exc}"
            ) from exc

    async def stream_text(  # type: ignore[override]
        self,
        messages: List[Dict[str, str]],
        model_config: ModelConfig,
        seed: Optional[int] = None,
        format_type: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream text generation using async OpenAI-compatible API."""
        accumulated: List[str] = []
        try:
            options = self._prepare_options(model_config, seed, format_type)
            stream = await self._get_client(model_config).chat.completions.create(
                messages=cast(Iterable[ChatCompletionMessageParam], messages),
                model=model_config.name,
                stream=True,
                **options,
            )
            stream = cast(AsyncStream[ChatCompletionChunk], stream)
            async for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    accumulated.append(delta)
                    yield delta
        except Exception as exc:
            raise ModelProviderError(f"OpenAI async streaming failed: {exc}") from exc
        finally:
            if accumulated:
                _append_debug_log(messages, model_config.name, "".join(accumulated))

    async def is_model_available(self, model_config: ModelConfig) -> bool:
        """Check if server model listing is reachable."""
        try:
            await self._get_client(model_config).models.list()
            return True
        except Exception:
            return False

    async def download_model(self, model_config: ModelConfig) -> None:
        """Download a model through external server tooling."""
        print("Model downloads are managed by the configured inference server.")
        print(
            f"Ensure the model '{model_config.name}' is available at {self._resolve_base_url(model_config)}."
        )

    async def get_supported_providers(self) -> List[str]:
        """Get list of supported providers."""
        return ["openai_async"]
