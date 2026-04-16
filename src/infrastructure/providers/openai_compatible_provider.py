"""OpenAI-compatible model provider implementation."""

import json
import random
import re
from typing import Any, AsyncGenerator, Dict, List, Optional
from urllib.parse import urlparse, urlunparse

from application.interfaces.model_provider import ModelProvider
from domain.exceptions import ModelProviderError
from domain.value_objects.model_config import ModelConfig


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


class OpenAICompatibleProvider(ModelProvider):
    """OpenAI-compatible model provider implementation."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434/v1",
        context_length: int = 16384,
        randomize_seed: bool = True,
    ):
        self.base_url = _normalize_base_url(base_url)
        self.context_length = context_length
        self.randomize_seed = randomize_seed
        self.clients: Dict[str, Any] = {}
        self._ensure_requests_installed()

    def _ensure_requests_installed(self):
        """Ensure requests package is installed."""
        try:
            import requests  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "Package 'requests' is required for OpenAICompatibleProvider. "
                "Install dependencies from requirements.txt before running."
            ) from exc

    def _resolve_base_url(self, model_config: ModelConfig) -> str:
        """Resolve request base URL from model config override or provider default."""
        if model_config.host:
            return _normalize_base_url(model_config.host)
        return self.base_url

    def _filter_think_tags(self, text: str) -> str:
        """Remove <think>...</think> tags from text while preserving the rest."""
        filtered = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        filtered = re.sub(r"<think>.*", "", filtered, flags=re.DOTALL)
        filtered = re.sub(r"</think>.*", "", filtered, flags=re.DOTALL)
        filtered = re.sub(r"(.*?)</think>.*", r"\1", filtered, flags=re.DOTALL)
        return filtered

    def _estimate_token_count(self, messages: List[Dict[str, str]]) -> int:
        """Estimate token count for messages using multiple methods."""
        total_text = ""
        for message in messages:
            role = message.get("role", "")
            content = message.get("content", "")
            total_text += f"{role}: {content}\n"

        try:
            import tiktoken

            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(total_text))
        except ImportError:
            pass
        except Exception:
            pass

        word_count = len(total_text.split())
        estimated_tokens = int(word_count * 1.33)
        message_overhead = len(messages) * 10
        return estimated_tokens + message_overhead

    def _log_prompt_stats(
        self, messages: List[Dict[str, str]], model_config: ModelConfig
    ):
        """Log prompt statistics including token count."""
        token_count = self._estimate_token_count(messages)
        total_chars = sum(len(msg.get("content", "")) for msg in messages)

        role_counts: Dict[str, int] = {}
        for msg in messages:
            role = msg.get("role", "unknown")
            role_counts[role] = role_counts.get(role, 0) + 1

        print(f"[PROMPT STATS] Estimated tokens: {token_count:,}")
        print(f"[PROMPT STATS] Total characters: {total_chars:,}")
        print(f"[PROMPT STATS] Message count: {len(messages)}")
        print(f"[PROMPT STATS] Messages by role: {role_counts}")

        context_length = model_config.parameters.get("max_tokens", self.context_length)
        if token_count > context_length * 0.8:
            print(
                f"[PROMPT STATS] WARNING: Prompt uses {token_count:,} tokens, approaching context limit of {context_length:,}"
            )
        elif token_count > context_length * 0.6:
            print(
                f"[PROMPT STATS] INFO: Prompt uses {token_count:,} tokens ({token_count / context_length * 100:.1f}% of {context_length:,} context limit)"
            )

    def _display_debug_prompt(
        self, messages: List[Dict[str, str]], model_config: ModelConfig
    ):
        """Display the full prompt messages in debug mode."""
        print(f"\n{'=' * 80}")
        print(f"DEBUG: Full Prompt for {model_config.name}")
        print(f"{'=' * 80}")
        for index, message in enumerate(messages, 1):
            role = message.get("role", "unknown")
            content = message.get("content", "")
            print(f"\n--- Message {index} ({role.upper()}) ---")
            print(content)
        print(f"{'=' * 80}\n")

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
        """Generate text using an OpenAI-compatible API."""
        try:
            if stream:
                return await self._generate_text_with_streaming(
                    messages=messages,
                    model_config=model_config,
                    seed=seed,
                    format_type=format_type,
                    debug=debug,
                )

            return await self._generate_text_non_streaming(
                messages=messages,
                model_config=model_config,
                seed=seed,
                format_type=format_type,
                min_word_count=min_word_count,
                debug=debug,
            )
        except Exception as exc:
            raise ModelProviderError(
                f"OpenAI-compatible generation failed: {exc}"
            ) from exc

    async def _generate_text_non_streaming(
        self,
        messages: List[Dict[str, str]],
        model_config: ModelConfig,
        seed: Optional[int] = None,
        format_type: Optional[str] = None,
        min_word_count: int = 1,
        debug: bool = False,
    ) -> str:
        """Generate text without streaming."""
        try:
            options = self._prepare_options(model_config, seed, format_type)

            if debug:
                self._display_debug_prompt(messages, model_config)

            self._log_prompt_stats(messages, model_config)

            print(f"\n[CHAT REQUEST] Model: {model_config.name}")
            print(f"[CHAT REQUEST] Provider: {model_config.provider}")
            if model_config.host:
                print(f"[CHAT REQUEST] Host: {model_config.host}")
            print(f"[CHAT REQUEST] Options: {options}")
            print(f"[CHAT REQUEST] Format: {format_type or 'text'}")
            print(f"[CHAT REQUEST] Seed: {seed}")
            print(f"[CHAT REQUEST] Min word count: {min_word_count}")
            print()

            payload = {"model": model_config.name, "messages": messages, **options}
            response = await self._make_request(payload, model_config)

            response_text = (
                response.get("choices", [{}])[0].get("message", {}).get("content", "")
            )
            response_text = self._filter_think_tags(response_text)

            if len(response_text.split()) < min_word_count:
                messages.append({"role": "assistant", "content": response_text})
                messages.append(
                    {
                        "role": "user",
                        "content": f"Please continue and expand on this response to reach at least {min_word_count} words.",
                    }
                )

                payload = {"model": model_config.name, "messages": messages, **options}
                response = await self._make_request(payload, model_config)
                response_text = (
                    response.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                response_text = self._filter_think_tags(response_text)

            return response_text
        except Exception as exc:
            raise ModelProviderError(
                f"OpenAI-compatible generation failed: {exc}"
            ) from exc

    async def _generate_text_with_streaming(
        self,
        messages: List[Dict[str, str]],
        model_config: ModelConfig,
        seed: Optional[int] = None,
        format_type: Optional[str] = None,
        debug: bool = False,
    ) -> str:
        """Generate text with streaming output for debug mode."""
        if debug:
            self._display_debug_prompt(messages, model_config)

        self._log_prompt_stats(messages, model_config)

        full_response = ""
        async for chunk in self.stream_text(
            messages=messages,
            model_config=model_config,
            seed=seed,
            format_type=format_type,
        ):
            print(chunk, end="", flush=True)
            full_response += chunk
        print()

        return self._filter_think_tags(full_response)

    async def generate_json(
        self,
        messages: List[Dict[str, str]],
        model_config: ModelConfig,
        required_attributes: List[str],
        seed: Optional[int] = None,
        debug: bool = False,
    ) -> Dict[str, Any]:
        """Generate JSON response using an OpenAI-compatible API."""
        try:
            if debug:
                self._display_debug_prompt(messages, model_config)
                print(f"[DEBUG] Generating JSON response using {model_config.name}...")
                print(f"[DEBUG] Required attributes: {required_attributes}")

            self._log_prompt_stats(messages, model_config)

            response_text = await self._generate_text_non_streaming_no_stats(
                messages=messages,
                model_config=model_config,
                seed=seed,
                format_type="json",
                debug=debug,
            )

            if debug:
                print(f"[DEBUG] Raw JSON response: {response_text}")

            try:
                response_data = json.loads(response_text)
                if debug:
                    print(f"[DEBUG] Parsed JSON: {response_data}")
                return response_data
            except json.JSONDecodeError as exc:
                if debug:
                    print(f"[DEBUG] JSON parsing failed: {exc}")
                    print("[DEBUG] Attempting to extract JSON from response...")

                json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
                if json_match:
                    try:
                        response_data = json.loads(json_match.group())
                        if debug:
                            print(
                                f"[DEBUG] Successfully extracted JSON: {response_data}"
                            )
                        return response_data
                    except json.JSONDecodeError:
                        pass

                raise ModelProviderError(f"Failed to parse JSON response: {exc}")
        except Exception as exc:
            raise ModelProviderError(
                f"OpenAI-compatible JSON generation failed: {exc}"
            ) from exc

    async def stream_text(
        self,
        messages: List[Dict[str, str]],
        model_config: ModelConfig,
        seed: Optional[int] = None,
        format_type: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream text generation using an OpenAI-compatible API."""
        try:
            options = self._prepare_options(model_config, seed, format_type)

            self._log_prompt_stats(messages, model_config)

            print(f"\n[CHAT REQUEST] Model: {model_config.name}")
            print(f"[CHAT REQUEST] Provider: {model_config.provider}")
            if model_config.host:
                print(f"[CHAT REQUEST] Host: {model_config.host}")
            print(f"[CHAT REQUEST] Options: {options}")
            print(f"[CHAT REQUEST] Format: {format_type or 'text'}")
            print(f"[CHAT REQUEST] Seed: {seed}")
            print("[CHAT REQUEST] Mode: streaming")
            print()

            payload = {
                "model": model_config.name,
                "messages": messages,
                "stream": True,
                **options,
            }

            async for chunk in self._stream_request(payload, model_config):
                if chunk.get("choices") and chunk["choices"][0].get("delta", {}).get(
                    "content"
                ):
                    yield chunk["choices"][0]["delta"]["content"]
        except Exception as exc:
            raise ModelProviderError(
                f"OpenAI-compatible streaming failed: {exc}"
            ) from exc

    async def is_model_available(self, model_config: ModelConfig) -> bool:
        """Check if a model is available via /v1/models."""
        try:
            import requests

            response = requests.get(
                f"{self._resolve_base_url(model_config)}/models", timeout=5
            )
            return response.status_code == 200
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
        return ["openai_compatible", "ollama"]

    async def _make_request(
        self, payload: Dict[str, Any], model_config: ModelConfig
    ) -> Dict[str, Any]:
        """Make a request to the OpenAI-compatible API."""
        import requests

        response = requests.post(
            f"{self._resolve_base_url(model_config)}/chat/completions",
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        return response.json()

    async def _stream_request(self, payload: Dict[str, Any], model_config: ModelConfig):
        """Make a streaming request to the OpenAI-compatible API."""
        import requests

        response = requests.post(
            f"{self._resolve_base_url(model_config)}/chat/completions",
            json=payload,
            stream=True,
            timeout=120,
        )
        response.raise_for_status()

        for line in response.iter_lines():
            if not line:
                continue

            decoded = line.decode("utf-8")
            if not decoded.startswith("data: "):
                continue

            data = decoded[6:]
            if data == "[DONE]":
                break

            try:
                yield json.loads(data)
            except json.JSONDecodeError:
                continue

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

        if "max_tokens" not in options:
            options["max_tokens"] = self.context_length
        elif options["max_tokens"] > self.context_length:
            print(
                f"[OPENAI COMPATIBLE] Warning: Requested max_tokens {options['max_tokens']} exceeds infrastructure limit {self.context_length}, capping to {self.context_length}"
            )
            options["max_tokens"] = self.context_length

        if seed is not None:
            should_randomize = self.randomize_seed and not model_config.parameters.get(
                "static_seed", False
            )
            if should_randomize:
                random_offset = random.randint(1, 10000)
                options["seed"] = seed + random_offset
                print(
                    f"[OPENAI COMPATIBLE] Seed randomized: {seed} + {random_offset} = {options['seed']}"
                )
            else:
                options["seed"] = seed
                print(f"[OPENAI COMPATIBLE] Using static seed: {seed}")

        if format_type == "json":
            options["response_format"] = {"type": "json_object"}
            if "temperature" not in options:
                options["temperature"] = 0

        if "temperature" not in options:
            options["temperature"] = 0.7

        if "top_p" not in options:
            options["top_p"] = 0.9

        print(
            f"[OPENAI COMPATIBLE] Context length: {options['max_tokens']} (from model config)"
        )

        return options

    async def _generate_text_non_streaming_no_stats(
        self,
        messages: List[Dict[str, str]],
        model_config: ModelConfig,
        seed: Optional[int] = None,
        format_type: Optional[str] = None,
        min_word_count: int = 1,
        debug: bool = False,
    ) -> str:
        """Generate text without streaming and without logging stats."""
        try:
            options = self._prepare_options(model_config, seed, format_type)

            if debug:
                self._display_debug_prompt(messages, model_config)

            print(f"\n[CHAT REQUEST] Model: {model_config.name}")
            print(f"[CHAT REQUEST] Provider: {model_config.provider}")
            if model_config.host:
                print(f"[CHAT REQUEST] Host: {model_config.host}")
            print(f"[CHAT REQUEST] Options: {options}")
            print(f"[CHAT REQUEST] Format: {format_type or 'text'}")
            print(f"[CHAT REQUEST] Seed: {seed}")
            print(f"[CHAT REQUEST] Min word count: {min_word_count}")
            print()

            payload = {"model": model_config.name, "messages": messages, **options}
            response = await self._make_request(payload, model_config)

            response_text = (
                response.get("choices", [{}])[0].get("message", {}).get("content", "")
            )
            response_text = self._filter_think_tags(response_text)

            if len(response_text.split()) < min_word_count:
                messages.append({"role": "assistant", "content": response_text})
                messages.append(
                    {
                        "role": "user",
                        "content": f"Please continue and expand on this response to reach at least {min_word_count} words.",
                    }
                )

                payload = {"model": model_config.name, "messages": messages, **options}
                response = await self._make_request(payload, model_config)
                response_text = (
                    response.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                response_text = self._filter_think_tags(response_text)

            return response_text
        except Exception as exc:
            raise ModelProviderError(
                f"OpenAI-compatible generation failed: {exc}"
            ) from exc

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
        try:
            if stream:
                return await self._generate_multistep_conversation_with_streaming(
                    user_messages=user_messages,
                    model_config=model_config,
                    system_message=system_message,
                    seed=seed,
                    debug=debug,
                )

            return await self._generate_multistep_conversation_non_streaming(
                user_messages=user_messages,
                model_config=model_config,
                system_message=system_message,
                seed=seed,
                debug=debug,
            )
        except Exception as exc:
            raise ModelProviderError(
                f"OpenAI-compatible multi-step conversation failed: {exc}"
            ) from exc

    async def _generate_multistep_conversation_non_streaming(
        self,
        user_messages: List[str],
        model_config: ModelConfig,
        system_message: Optional[str] = None,
        seed: Optional[int] = None,
        debug: bool = False,
    ) -> str:
        """Generate text through a multi-step conversation without streaming."""
        try:
            options = self._prepare_options(model_config, seed, None)

            if debug:
                print(f"\n{'=' * 80}")
                print(f"DEBUG: Multi-step Conversation for {model_config.name}")
                print(f"{'=' * 80}")
                print(f"System Message: {system_message or 'None'}")
                print(f"User Messages: {len(user_messages)}")
                for index, message in enumerate(user_messages, 1):
                    preview = f"{message[:100]}{'...' if len(message) > 100 else ''}"
                    print(f"  {index}. {preview}")
                print(f"{'=' * 80}\n")

            conversation_messages = []
            if system_message:
                conversation_messages.append(
                    {"role": "system", "content": system_message}
                )

            final_response = ""
            for index, user_message in enumerate(user_messages, 1):
                if debug:
                    print(
                        f"[CONVERSATION] Step {index}/{len(user_messages)}: Processing user message"
                    )
                    print(
                        f"[CONVERSATION] User: {user_message[:100]}{'...' if len(user_message) > 100 else ''}"
                    )

                conversation_messages.append({"role": "user", "content": user_message})
                payload = {
                    "model": model_config.name,
                    "messages": conversation_messages,
                    **options,
                }
                response = await self._make_request(payload, model_config)
                response_text = (
                    response.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                response_text = self._filter_think_tags(response_text)

                if debug:
                    print(
                        f"[CONVERSATION] Step {index} Response: {response_text[:100]}{'...' if len(response_text) > 100 else ''}"
                    )

                conversation_messages.append(
                    {"role": "assistant", "content": response_text}
                )
                final_response = response_text

            if debug:
                print(f"[CONVERSATION] Completed {len(user_messages)} steps")
                print(
                    f"[CONVERSATION] Final response length: {len(final_response)} characters"
                )

            return final_response
        except Exception as exc:
            raise ModelProviderError(
                f"OpenAI-compatible multi-step conversation failed: {exc}"
            ) from exc

    async def _generate_multistep_conversation_with_streaming(
        self,
        user_messages: List[str],
        model_config: ModelConfig,
        system_message: Optional[str] = None,
        seed: Optional[int] = None,
        debug: bool = False,
    ) -> str:
        """Generate text through a multi-step conversation with streaming output."""
        try:
            if debug:
                print(f"\n{'=' * 80}")
                print(
                    f"DEBUG: Multi-step Conversation (Streaming) for {model_config.name}"
                )
                print(f"{'=' * 80}")
                print(f"System Message: {system_message or 'None'}")
                print(f"User Messages: {len(user_messages)}")
                for index, message in enumerate(user_messages, 1):
                    preview = f"{message[:100]}{'...' if len(message) > 100 else ''}"
                    print(f"  {index}. {preview}")
                print(f"{'=' * 80}\n")

            conversation_messages = []
            if system_message:
                conversation_messages.append(
                    {"role": "system", "content": system_message}
                )

            final_response = ""
            for index, user_message in enumerate(user_messages, 1):
                if debug:
                    print(
                        f"[CONVERSATION] Step {index}/{len(user_messages)}: Processing user message"
                    )
                    print(
                        f"[CONVERSATION] User: {user_message[:100]}{'...' if len(user_message) > 100 else ''}"
                    )

                conversation_messages.append({"role": "user", "content": user_message})

                print(f"\n[CONVERSATION] Step {index} Response:")
                print(f"{'=' * 40}")

                response_text = ""
                payload_messages = list(conversation_messages)
                async for chunk in self.stream_text(
                    messages=payload_messages,
                    model_config=model_config,
                    seed=seed,
                    format_type=None,
                ):
                    print(chunk, end="", flush=True)
                    response_text += chunk

                print(f"\n{'=' * 40}")
                response_text = self._filter_think_tags(response_text)

                if debug:
                    print(
                        f"[CONVERSATION] Step {index} Response Length: {len(response_text)} characters"
                    )

                conversation_messages.append(
                    {"role": "assistant", "content": response_text}
                )
                final_response = response_text

            if debug:
                print(f"[CONVERSATION] Completed {len(user_messages)} steps")
                print(
                    f"[CONVERSATION] Final response length: {len(final_response)} characters"
                )

            return final_response
        except Exception as exc:
            raise ModelProviderError(
                f"OpenAI-compatible multi-step conversation streaming failed: {exc}"
            ) from exc
