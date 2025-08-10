"""Ollama model provider implementation."""

import asyncio
import json
import random
import subprocess
import sys
import re
from typing import List, Dict, Any, Optional, AsyncGenerator
from domain.value_objects.model_config import ModelConfig
from domain.exceptions import ModelProviderError
from application.interfaces.model_provider import ModelProvider


class OllamaProvider(ModelProvider):
    """Ollama model provider implementation."""
    
    def __init__(self, host: str = "127.0.0.1:11434"):
        self.host = host
        self.clients = {}
        self._ensure_ollama_installed()
    
    def _ensure_ollama_installed(self):
        """Ensure ollama package is installed."""
        try:
            import ollama
        except ImportError:
            print("Package ollama not found. Installing...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "ollama"])
            import ollama
    
    def _filter_think_tags(self, text: str) -> str:
        """Remove <think>...</think> tags from text while preserving the rest."""
        # Remove complete think tags and their content
        filtered = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        # Remove any remaining incomplete think tags
        filtered = re.sub(r'<think>.*', '', filtered, flags=re.DOTALL)
        # Remove any remaining incomplete closing tags (but preserve text before them)
        filtered = re.sub(r'</think>.*', '', filtered, flags=re.DOTALL)
        # Handle the case where we have text followed by </think> without a <think>
        # This regex captures everything up to </think> and removes the </think> and everything after
        filtered = re.sub(r'(.*?)</think>.*', r'\1', filtered, flags=re.DOTALL)
        return filtered
    
    def _display_debug_prompt(self, messages: List[Dict[str, str]], model_config: ModelConfig):
        """Display the full prompt messages in debug mode."""
        print(f"\n{'='*80}")
        print(f"DEBUG: Full Prompt for {model_config.name}")
        print(f"{'='*80}")
        for i, message in enumerate(messages, 1):
            role = message.get('role', 'unknown')
            content = message.get('content', '')
            print(f"\n--- Message {i} ({role.upper()}) ---")
            print(content)
        print(f"{'='*80}\n")
    
    async def generate_text(
        self,
        messages: List[Dict[str, str]],
        model_config: ModelConfig,
        seed: Optional[int] = None,
        format_type: Optional[str] = None,
        min_word_count: int = 1,
        debug: bool = False,
        stream: bool = False
    ) -> str:
        """Generate text using Ollama."""
        try:
            if stream:
                # Use streaming for stream mode
                return await self._generate_text_with_streaming(
                    messages=messages,
                    model_config=model_config,
                    seed=seed,
                    format_type=format_type,
                    debug=debug
                )
            else:
                # Use non-streaming for normal mode
                return await self._generate_text_non_streaming(
                    messages=messages,
                    model_config=model_config,
                    seed=seed,
                    format_type=format_type,
                    min_word_count=min_word_count,
                    debug=debug
                )
        except Exception as e:
            raise ModelProviderError(f"Ollama generation failed: {e}") from e
    
    async def _generate_text_non_streaming(
        self,
        messages: List[Dict[str, str]],
        model_config: ModelConfig,
        seed: Optional[int] = None,
        format_type: Optional[str] = None,
        min_word_count: int = 1,
        debug: bool = False
    ) -> str:
        """Generate text without streaming (original implementation)."""
        try:
            client = await self._get_client(model_config)
            options = self._prepare_options(model_config, seed, format_type)
            
            # Display debug prompt if enabled
            if debug:
                self._display_debug_prompt(messages, model_config)
            
            # Output model and options details
            print(f"\n[CHAT REQUEST] Model: {model_config.name}")
            print(f"[CHAT REQUEST] Provider: {model_config.provider}")
            if model_config.host:
                print(f"[CHAT REQUEST] Host: {model_config.host}")
            print(f"[CHAT REQUEST] Options: {options}")
            print(f"[CHAT REQUEST] Format: {format_type or 'text'}")
            print(f"[CHAT REQUEST] Seed: {seed}")
            print(f"[CHAT REQUEST] Min word count: {min_word_count}")
            if options.get('think'):
                print(f"[CHAT REQUEST] Thinking: ENABLED")
            print()
            
            response = await asyncio.to_thread(
                client.chat,
                model=model_config.name,
                messages=messages,
                options=options
            )
            
            # Add a short delay to allow Ollama time to unload the model
            await asyncio.sleep(5)
            
            response_text = response['message']['content']
            
            # Handle thinking output if present
            if 'thinking' in response['message'] and response['message']['thinking']:
                thinking_text = response['message']['thinking']
                # Combine thinking and content for streaming output
                response_text = f"<thinking>{thinking_text}</thinking>\n\n{response_text}"
            
            # Filter out think tags (for backward compatibility with models that use <think> tags)
            response_text = self._filter_think_tags(response_text)
            
            # Ensure minimum word count
            word_count = len(response_text.split())
            if word_count < min_word_count:
                # Retry with more specific prompt
                messages.append({"role": "assistant", "content": response_text})
                messages.append({"role": "user", "content": f"Please continue and expand on this response to reach at least {min_word_count} words."})
                
                response = await asyncio.to_thread(
                    client.chat,
                    model=model_config.name,
                    messages=messages,
                    options=options
                )
                
                # Add a short delay to allow Ollama time to unload the model
                await asyncio.sleep(5)
                
                response_text = response['message']['content']
                
                # Handle thinking output if present in continuation
                if 'thinking' in response['message'] and response['message']['thinking']:
                    thinking_text = response['message']['thinking']
                    response_text = f"<thinking>{thinking_text}</thinking>\n\n{response_text}"
                
                # Filter think tags from the continuation as well
                response_text = self._filter_think_tags(response_text)
            
            return response_text
            
        except Exception as e:
            raise ModelProviderError(f"Ollama generation failed: {e}") from e
    
    async def _generate_text_with_streaming(
        self,
        messages: List[Dict[str, str]],
        model_config: ModelConfig,
        seed: Optional[int] = None,
        format_type: Optional[str] = None,
        debug: bool = False
    ) -> str:
        """Generate text with streaming output for debug mode."""
        # Display debug prompt if enabled
        if debug:
            self._display_debug_prompt(messages, model_config)
        
        full_response = ""
        async for chunk in self.stream_text(
            messages=messages,
            model_config=model_config,
            seed=seed,
            format_type=format_type
        ):
            print(chunk, end="", flush=True)
            full_response += chunk
        print()  # New line after streaming
        
        # Filter out think tags from the complete response
        filtered_response = self._filter_think_tags(full_response)
        return filtered_response
    
    async def generate_json(
        self,
        messages: List[Dict[str, str]],
        model_config: ModelConfig,
        required_attributes: List[str],
        seed: Optional[int] = None,
        debug: bool = False
    ) -> Dict[str, Any]:
        """Generate JSON response using Ollama."""
        try:
            # Display debug prompt if enabled
            if debug:
                self._display_debug_prompt(messages, model_config)
                print(f"[DEBUG] Generating JSON response using {model_config.name}...")
                print(f"[DEBUG] Required attributes: {required_attributes}")
            
            # Use the existing non-streaming implementation for JSON
            response_text = await self._generate_text_non_streaming(
                messages=messages,
                model_config=model_config,
                seed=seed,
                format_type="json",
                debug=debug
            )
            
            if debug:
                print(f"[DEBUG] Raw JSON response: {response_text}")
            
            # Parse JSON response
            try:
                import json
                response_data = json.loads(response_text)
                
                if debug:
                    print(f"[DEBUG] Parsed JSON: {response_data}")
                
                return response_data
                
            except json.JSONDecodeError as e:
                if debug:
                    print(f"[DEBUG] JSON parsing failed: {e}")
                    print(f"[DEBUG] Attempting to extract JSON from response...")
                
                # Try to extract JSON from the response
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    try:
                        response_data = json.loads(json_match.group())
                        if debug:
                            print(f"[DEBUG] Successfully extracted JSON: {response_data}")
                        return response_data
                    except json.JSONDecodeError:
                        pass
                
                raise ModelProviderError(f"Failed to parse JSON response: {e}")
                
        except Exception as e:
            raise ModelProviderError(f"Ollama JSON generation failed: {e}") from e
    
    async def stream_text(
        self,
        messages: List[Dict[str, str]],
        model_config: ModelConfig,
        seed: Optional[int] = None,
        format_type: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Stream text generation using Ollama."""
        try:
            client = await self._get_client(model_config)
            options = self._prepare_options(model_config, seed, format_type)
            
            # Output model and options details
            print(f"\n[CHAT REQUEST] Model: {model_config.name}")
            print(f"[CHAT REQUEST] Provider: {model_config.provider}")
            if model_config.host:
                print(f"[CHAT REQUEST] Host: {model_config.host}")
            print(f"[CHAT REQUEST] Options: {options}")
            print(f"[CHAT REQUEST] Format: {format_type or 'text'}")
            print(f"[CHAT REQUEST] Seed: {seed}")
            print(f"[CHAT REQUEST] Mode: streaming")
            if options.get('think'):
                print(f"[CHAT REQUEST] Thinking: ENABLED")
            print()
            
            # Stream response
            stream = await asyncio.to_thread(
                client.chat,
                model=model_config.name,
                messages=messages,
                options=options,
                stream=True
            )
            
            # Add a short delay to allow Ollama time to unload the model after streaming completes
            # Note: The delay will be added after the streaming loop completes
            
            buffer = ""
            in_think_tag = False
            thinking_buffer = ""
            content_buffer = ""
            thinking_complete = False
            
            for chunk in stream:
                # Handle thinking output (new Ollama thinking feature)
                if 'message' in chunk and 'thinking' in chunk['message'] and chunk['message']['thinking']:
                    thinking_buffer += chunk['message']['thinking']
                    # Yield thinking content as it comes
                    yield chunk['message']['thinking']
                
                # Handle content output
                if 'message' in chunk and 'content' in chunk['message'] and chunk['message']['content']:
                    content = chunk['message']['content']
                    content_buffer += content
                    
                    # Process the buffer to handle legacy think tags
                    while True:
                        if not in_think_tag:
                            # Look for start of think tag
                            think_start = content_buffer.find('<think>')
                            if think_start != -1:
                                # Yield content before think tag
                                if think_start > 0:
                                    yield content_buffer[:think_start]
                                # Remove content up to and including think tag start
                                content_buffer = content_buffer[think_start + 7:]  # 7 is len('<think>')
                                in_think_tag = True
                                continue
                            else:
                                # No think tag found, yield the buffer
                                if content_buffer:
                                    yield content_buffer
                                    content_buffer = ""
                                break
                        else:
                            # We're inside a think tag, look for end
                            think_end = content_buffer.find('</think>')
                            if think_end != -1:
                                # Remove content up to and including think tag end
                                content_buffer = content_buffer[think_end + 8:]  # 8 is len('</think>')
                                in_think_tag = False
                                continue
                            else:
                                # Think tag not complete, keep buffering
                                break
            
            # Yield any remaining content (outside of think tags)
            if content_buffer and not in_think_tag:
                yield content_buffer
            
            # Add a short delay to allow Ollama time to unload the model after streaming completes
            await asyncio.sleep(5)
                    
        except Exception as e:
            raise ModelProviderError(f"Ollama streaming failed: {e}") from e
    
    async def is_model_available(self, model_config: ModelConfig) -> bool:
        """Check if a model is available in Ollama."""
        try:
            client = await self._get_client(model_config)
            await asyncio.to_thread(client.show, model_config.name)
            return True
        except Exception:
            return False
    
    async def download_model(self, model_config: ModelConfig) -> None:
        """Download a model in Ollama."""
        try:
            client = await self._get_client(model_config)
            
            print(f"Downloading model {model_config.name}...")
            stream = await asyncio.to_thread(
                client.pull,
                model_config.name,
                stream=True
            )
            
            for chunk in stream:
                if 'completed' in chunk and 'total' in chunk:
                    progress = chunk['completed'] / chunk['total']
                    completed_size = chunk['completed'] / 1024**3
                    total_size = chunk['total'] / 1024**3
                    print(f"Downloading {model_config.name}: {progress * 100:.2f}% ({completed_size:.3f}GB/{total_size:.3f}GB)", end="\r")
                else:
                    print(f"{chunk.get('status', 'Unknown')} {model_config.name}", end="\r")
            
            print(f"\nModel {model_config.name} downloaded successfully!")
            
        except Exception as e:
            raise ModelProviderError(f"Failed to download model {model_config.name}: {e}") from e
    
    async def get_supported_providers(self) -> List[str]:
        """Get list of supported providers."""
        return ["ollama"]
    
    async def _get_client(self, model_config: ModelConfig):
        """Get or create Ollama client."""
        if model_config.name not in self.clients:
            import ollama
            host = model_config.host or self.host
            self.clients[model_config.name] = ollama.Client(host=host)
        
        return self.clients[model_config.name]
    
    def _prepare_options(
        self,
        model_config: ModelConfig,
        seed: Optional[int] = None,
        format_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Prepare options for Ollama API call."""
        options = model_config.parameters.copy()
        
        # Set default context length if not specified
        if 'num_ctx' not in options:
            options['num_ctx'] = 16384
        
        # Set seed if provided, with automatic randomness
        if seed is not None:
            # Add random offset to ensure variety in generation
            random_offset = random.randint(1, 10000)
            options['seed'] = seed + random_offset
        
        # Set format for JSON responses
        if format_type == "json":
            options['format'] = 'json'
            if 'temperature' not in options:
                options['temperature'] = 0
        
        # Enable thinking for models that support it
        # Currently supported: DeepSeek R1, Qwen 3, and others
        thinking_models = [
            "deepseek-r1", "deepseek-r1:8b", "deepseek-r1:32b",
            "qwen3", "qwen3:8b", "qwen3:32b"
        ]
        
        # Check if the model name contains any thinking model identifiers
        if any(thinking_model in model_config.name.lower() for thinking_model in thinking_models):
            options['think'] = True
        
        # Special handling for specific models
        if model_config.name == "huihui_ai/magistral-abliterated:24b":
            options['temperature'] = 0.7
        
        # Set keep_alive to 0 to unload model immediately after request
        options['keep_alive'] = 0
        
        return options 