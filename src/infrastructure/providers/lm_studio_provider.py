"""LM Studio model provider implementation."""

import asyncio
import json
import random
import re
from typing import List, Dict, Any, Optional, AsyncGenerator
from domain.value_objects.model_config import ModelConfig
from domain.exceptions import ModelProviderError
from application.interfaces.model_provider import ModelProvider


class LMStudioProvider(ModelProvider):
    """LM Studio model provider implementation."""
    
    def __init__(self, host: str = "127.0.0.1:1234", context_length: int = 16384, randomize_seed: bool = True):
        self.host = host
        self.context_length = context_length
        self.randomize_seed = randomize_seed
        self.clients = {}
        self._ensure_requests_installed()
    
    def _ensure_requests_installed(self):
        """Ensure requests package is installed."""
        try:
            import requests
        except ImportError:
            print("Package requests not found. Installing...")
            import subprocess
            import sys
            subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
            import requests
    
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
    
    def _estimate_token_count(self, messages: List[Dict[str, str]]) -> int:
        """Estimate token count for messages using multiple methods."""
        # Combine all message content
        total_text = ""
        for message in messages:
            role = message.get('role', '')
            content = message.get('content', '')
            # Include role tokens in estimation
            total_text += f"{role}: {content}\n"
        
        # Try tiktoken first (most accurate for OpenAI-compatible models)
        try:
            import tiktoken
            # Use cl100k_base encoding (GPT-4 tokenizer) as a reasonable approximation
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(total_text))
        except ImportError:
            # tiktoken not available, fall back to word-based estimation
            pass
        except Exception:
            # Other tiktoken errors, fall back to word-based estimation
            pass
        
        # Fallback to word-based estimation
        # Most models have roughly 1.3-1.5 tokens per word on average
        word_count = len(total_text.split())
        estimated_tokens = int(word_count * 1.33)
        
        # Add some tokens for message structure overhead
        message_overhead = len(messages) * 10  # ~10 tokens per message for role/structure
        
        return estimated_tokens + message_overhead
    
    def _log_prompt_stats(self, messages: List[Dict[str, str]], model_config: ModelConfig):
        """Log prompt statistics including token count."""
        token_count = self._estimate_token_count(messages)
        
        # Calculate total character count
        total_chars = sum(len(msg.get('content', '')) for msg in messages)
        
        # Count messages by role
        role_counts = {}
        for msg in messages:
            role = msg.get('role', 'unknown')
            role_counts[role] = role_counts.get(role, 0) + 1
        
        print(f"[PROMPT STATS] Estimated tokens: {token_count:,}")
        print(f"[PROMPT STATS] Total characters: {total_chars:,}")
        print(f"[PROMPT STATS] Message count: {len(messages)}")
        print(f"[PROMPT STATS] Messages by role: {role_counts}")
        
        # Warn if token count is very high
        context_length = model_config.parameters.get('max_tokens', self.context_length)
        if token_count > context_length * 0.8:  # Warn at 80% of context length
            print(f"[PROMPT STATS] ⚠️  WARNING: Prompt uses {token_count:,} tokens, approaching context limit of {context_length:,}")
        elif token_count > context_length * 0.6:  # Info at 60% of context length
            print(f"[PROMPT STATS] ℹ️  INFO: Prompt uses {token_count:,} tokens ({token_count/context_length*100:.1f}% of {context_length:,} context limit)")
    
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
        """Generate text using LM Studio."""
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
            raise ModelProviderError(f"LM Studio generation failed: {e}") from e
    
    async def _generate_text_non_streaming(
        self,
        messages: List[Dict[str, str]],
        model_config: ModelConfig,
        seed: Optional[int] = None,
        format_type: Optional[str] = None,
        min_word_count: int = 1,
        debug: bool = False
    ) -> str:
        """Generate text without streaming."""
        try:
            options = self._prepare_options(model_config, seed, format_type)
            
            # Display debug prompt if enabled
            if debug:
                self._display_debug_prompt(messages, model_config)
            
            # Log prompt statistics
            self._log_prompt_stats(messages, model_config)
            
            # Output model and options details
            print(f"\n[CHAT REQUEST] Model: {model_config.name}")
            print(f"[CHAT REQUEST] Provider: {model_config.provider}")
            if model_config.host:
                print(f"[CHAT REQUEST] Host: {model_config.host}")
            print(f"[CHAT REQUEST] Options: {options}")
            print(f"[CHAT REQUEST] Format: {format_type or 'text'}")
            print(f"[CHAT REQUEST] Seed: {seed}")
            print(f"[CHAT REQUEST] Min word count: {min_word_count}")
            print()
            
            # Prepare the request payload
            payload = {
                "messages": messages,
                **options
            }
            
            # Make the request to LM Studio
            response = await self._make_request(payload, model_config)
            
            response_text = response.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            # Filter out think tags if present
            response_text = self._filter_think_tags(response_text)
            
            # Ensure minimum word count
            word_count = len(response_text.split())
            if word_count < min_word_count:
                # Retry with more specific prompt
                messages.append({"role": "assistant", "content": response_text})
                messages.append({"role": "user", "content": f"Please continue and expand on this response to reach at least {min_word_count} words."})
                
                payload = {
                    "messages": messages,
                    **options
                }
                
                response = await self._make_request(payload, model_config)
                response_text = response.get('choices', [{}])[0].get('message', {}).get('content', '')
                
                # Filter think tags from the continuation as well
                response_text = self._filter_think_tags(response_text)
            
            return response_text
            
        except Exception as e:
            raise ModelProviderError(f"LM Studio generation failed: {e}") from e
    
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
        
        # Log prompt statistics
        self._log_prompt_stats(messages, model_config)
        
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
        """Generate JSON response using LM Studio."""
        try:
            # Display debug prompt if enabled
            if debug:
                self._display_debug_prompt(messages, model_config)
                print(f"[DEBUG] Generating JSON response using {model_config.name}...")
                print(f"[DEBUG] Required attributes: {required_attributes}")
            
            # Log prompt statistics
            self._log_prompt_stats(messages, model_config)
            
            # Use the existing non-streaming implementation for JSON
            response_text = await self._generate_text_non_streaming_no_stats(
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
                response_data = json.loads(response_text)
                
                if debug:
                    print(f"[DEBUG] Parsed JSON: {response_data}")
                
                return response_data
                
            except json.JSONDecodeError as e:
                if debug:
                    print(f"[DEBUG] JSON parsing failed: {e}")
                    print(f"[DEBUG] Attempting to extract JSON from response...")
                
                # Try to extract JSON from the response
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
            raise ModelProviderError(f"LM Studio JSON generation failed: {e}") from e
    
    async def stream_text(
        self,
        messages: List[Dict[str, str]],
        model_config: ModelConfig,
        seed: Optional[int] = None,
        format_type: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Stream text generation using LM Studio."""
        try:
            options = self._prepare_options(model_config, seed, format_type)
            
            # Log prompt statistics
            self._log_prompt_stats(messages, model_config)
            
            # Output model and options details
            print(f"\n[CHAT REQUEST] Model: {model_config.name}")
            print(f"[CHAT REQUEST] Provider: {model_config.provider}")
            if model_config.host:
                print(f"[CHAT REQUEST] Host: {model_config.host}")
            print(f"[CHAT REQUEST] Options: {options}")
            print(f"[CHAT REQUEST] Format: {format_type or 'text'}")
            print(f"[CHAT REQUEST] Seed: {seed}")
            print(f"[CHAT REQUEST] Mode: streaming")
            print()
            
            # Prepare the request payload
            payload = {
                "messages": messages,
                "stream": True,
                **options
            }
            
            # Stream response from LM Studio
            async for chunk in self._stream_request(payload, model_config):
                if chunk.get('choices') and chunk['choices'][0].get('delta', {}).get('content'):
                    content = chunk['choices'][0]['delta']['content']
                    yield content
                    
        except Exception as e:
            raise ModelProviderError(f"LM Studio streaming failed: {e}") from e
    
    async def is_model_available(self, model_config: ModelConfig) -> bool:
        """Check if a model is available in LM Studio."""
        try:
            # Try to make a simple request to check if the service is running
            import requests
            host = model_config.host or self.host
            response = requests.get(f"http://{host}/v1/models", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    async def download_model(self, model_config: ModelConfig) -> None:
        """Download a model in LM Studio."""
        # LM Studio handles model downloads through its own interface
        # This method is a no-op for LM Studio
        print(f"LM Studio handles model downloads through its own interface.")
        print(f"Please download the model '{model_config.name}' through the LM Studio application.")
    
    async def get_supported_providers(self) -> List[str]:
        """Get list of supported providers."""
        return ["lm_studio"]
    
    async def _make_request(self, payload: Dict[str, Any], model_config: ModelConfig) -> Dict[str, Any]:
        """Make a request to LM Studio API."""
        import requests
        
        host = model_config.host or self.host
        url = f"http://{host}/v1/chat/completions"
        
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        
        return response.json()
    
    async def _stream_request(self, payload: Dict[str, Any], model_config: ModelConfig):
        """Make a streaming request to LM Studio API."""
        import requests
        
        host = model_config.host or self.host
        url = f"http://{host}/v1/chat/completions"
        
        response = requests.post(url, json=payload, stream=True, timeout=120)
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data = line[6:]  # Remove 'data: ' prefix
                    if data == '[DONE]':
                        break
                    try:
                        chunk = json.loads(data)
                        yield chunk
                    except json.JSONDecodeError:
                        continue
    
    def _prepare_options(
        self,
        model_config: ModelConfig,
        seed: Optional[int] = None,
        format_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Prepare options for LM Studio API call."""
        options = model_config.parameters.copy()
        
        # Set context length from infrastructure config if not specified
        if 'max_tokens' not in options:
            options['max_tokens'] = self.context_length
        # If max_tokens is specified but exceeds infrastructure limit, cap it
        elif options['max_tokens'] > self.context_length:
            print(f"[LM STUDIO] Warning: Requested max_tokens {options['max_tokens']} exceeds infrastructure limit {self.context_length}, capping to {self.context_length}")
            options['max_tokens'] = self.context_length
        
        # Set seed if provided, with conditional randomness
        if seed is not None:
            # Check if we should randomize the seed
            should_randomize = self.randomize_seed and not model_config.parameters.get('static_seed', False)
            
            if should_randomize:
                # Add random offset to ensure variety in generation
                random_offset = random.randint(1, 10000)
                options['seed'] = seed + random_offset
                print(f"[LM STUDIO] Seed randomized: {seed} + {random_offset} = {options['seed']}")
            else:
                # Use exact seed without randomization
                options['seed'] = seed
                print(f"[LM STUDIO] Using static seed: {seed}")
        
        # Set format for JSON responses
        if format_type == "json":
            options['response_format'] = {"type": "json_object"}
            if 'temperature' not in options:
                options['temperature'] = 0
        
        # Set default temperature if not specified
        if 'temperature' not in options:
            options['temperature'] = 0.7
        
        # Set default top_p if not specified
        if 'top_p' not in options:
            options['top_p'] = 0.9
        
        # Log context length configuration for debugging
        if 'max_tokens' in options:
            print(f"[LM STUDIO] Context length: {options['max_tokens']} (from model config)")
        else:
            print(f"[LM STUDIO] Context length: {options['max_tokens']} (from infrastructure default)")
        
        return options
    
    async def _generate_text_non_streaming_no_stats(
        self,
        messages: List[Dict[str, str]],
        model_config: ModelConfig,
        seed: Optional[int] = None,
        format_type: Optional[str] = None,
        min_word_count: int = 1,
        debug: bool = False
    ) -> str:
        """Generate text without streaming and without logging stats (for internal use)."""
        try:
            options = self._prepare_options(model_config, seed, format_type)
            
            # Display debug prompt if enabled (but no stats logging)
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
            print()
            
            # Prepare the request payload
            payload = {
                "messages": messages,
                **options
            }
            
            # Make the request to LM Studio
            response = await self._make_request(payload, model_config)
            
            response_text = response.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            # Filter out think tags if present
            response_text = self._filter_think_tags(response_text)
            
            # Ensure minimum word count
            word_count = len(response_text.split())
            if word_count < min_word_count:
                # Retry with more specific prompt
                messages.append({"role": "assistant", "content": response_text})
                messages.append({"role": "user", "content": f"Please continue and expand on this response to reach at least {min_word_count} words."})
                
                payload = {
                    "messages": messages,
                    **options
                }
                
                response = await self._make_request(payload, model_config)
                response_text = response.get('choices', [{}])[0].get('message', {}).get('content', '')
                
                # Filter think tags from the continuation as well
                response_text = self._filter_think_tags(response_text)
            
            return response_text
            
        except Exception as e:
            raise ModelProviderError(f"LM Studio generation failed: {e}") from e
    
    async def generate_multistep_conversation(
        self,
        user_messages: List[str],
        model_config: ModelConfig,
        system_message: Optional[str] = None,
        seed: Optional[int] = None,
        debug: bool = False,
        stream: bool = False
    ) -> str:
        """Generate text through a multi-step conversation with memory."""
        try:
            if stream:
                # Use streaming for stream mode
                return await self._generate_multistep_conversation_with_streaming(
                    user_messages=user_messages,
                    model_config=model_config,
                    system_message=system_message,
                    seed=seed,
                    debug=debug
                )
            else:
                # Use non-streaming for normal mode
                return await self._generate_multistep_conversation_non_streaming(
                    user_messages=user_messages,
                    model_config=model_config,
                    system_message=system_message,
                    seed=seed,
                    debug=debug
                )
        except Exception as e:
            raise ModelProviderError(f"LM Studio multi-step conversation failed: {e}") from e
    
    async def _generate_multistep_conversation_non_streaming(
        self,
        user_messages: List[str],
        model_config: ModelConfig,
        system_message: Optional[str] = None,
        seed: Optional[int] = None,
        debug: bool = False
    ) -> str:
        """Generate text through a multi-step conversation without streaming."""
        try:
            options = self._prepare_options(model_config, seed, None)
            
            # Display debug information if enabled
            if debug:
                print(f"\n{'='*80}")
                print(f"DEBUG: Multi-step Conversation for {model_config.name}")
                print(f"{'='*80}")
                print(f"System Message: {system_message or 'None'}")
                print(f"User Messages: {len(user_messages)}")
                for i, msg in enumerate(user_messages, 1):
                    print(f"  {i}. {msg[:100]}{'...' if len(msg) > 100 else ''}")
                print(f"{'='*80}\n")
            
            # Initialize conversation memory
            conversation_messages = []
            
            # Add system message if provided
            if system_message:
                conversation_messages.append({"role": "system", "content": system_message})
            
            # Process each user message sequentially
            final_response = ""
            for i, user_message in enumerate(user_messages, 1):
                if debug:
                    print(f"[CONVERSATION] Step {i}/{len(user_messages)}: Processing user message")
                    print(f"[CONVERSATION] User: {user_message[:100]}{'...' if len(user_message) > 100 else ''}")
                
                # Add user message to conversation
                conversation_messages.append({"role": "user", "content": user_message})
                
                # Prepare the request payload
                payload = {
                    "messages": conversation_messages,
                    **options
                }
                
                # Generate response
                response = await self._make_request(payload, model_config)
                response_text = response.get('choices', [{}])[0].get('message', {}).get('content', '')
                
                # Filter out think tags if present
                response_text = self._filter_think_tags(response_text)
                
                if debug:
                    print(f"[CONVERSATION] Step {i} Response: {response_text[:100]}{'...' if len(response_text) > 100 else ''}")
                
                # Add assistant response to conversation
                conversation_messages.append({"role": "assistant", "content": response_text})
                
                # Store final response
                final_response = response_text
            
            if debug:
                print(f"[CONVERSATION] Completed {len(user_messages)} steps")
                print(f"[CONVERSATION] Final response length: {len(final_response)} characters")
            
            return final_response
            
        except Exception as e:
            raise ModelProviderError(f"LM Studio multi-step conversation failed: {e}") from e
    
    async def _generate_multistep_conversation_with_streaming(
        self,
        user_messages: List[str],
        model_config: ModelConfig,
        system_message: Optional[str] = None,
        seed: Optional[int] = None,
        debug: bool = False
    ) -> str:
        """Generate text through a multi-step conversation with streaming output."""
        try:
            options = self._prepare_options(model_config, seed, None)
            
            # Display debug information if enabled
            if debug:
                print(f"\n{'='*80}")
                print(f"DEBUG: Multi-step Conversation (Streaming) for {model_config.name}")
                print(f"{'='*80}")
                print(f"System Message: {system_message or 'None'}")
                print(f"User Messages: {len(user_messages)}")
                for i, msg in enumerate(user_messages, 1):
                    print(f"  {i}. {msg[:100]}{'...' if len(msg) > 100 else ''}")
                print(f"{'='*80}\n")
            
            # Initialize conversation memory
            conversation_messages = []
            
            # Add system message if provided
            if system_message:
                conversation_messages.append({"role": "system", "content": system_message})
            
            # Process each user message sequentially
            final_response = ""
            for i, user_message in enumerate(user_messages, 1):
                if debug:
                    print(f"[CONVERSATION] Step {i}/{len(user_messages)}: Processing user message")
                    print(f"[CONVERSATION] User: {user_message[:100]}{'...' if len(user_message) > 100 else ''}")
                
                # Add user message to conversation
                conversation_messages.append({"role": "user", "content": user_message})
                
                # Generate streaming response
                print(f"\n[CONVERSATION] Step {i} Response:")
                print(f"{'='*40}")
                
                response_text = ""
                async for chunk in self.stream_text(
                    messages=conversation_messages,
                    model_config=model_config,
                    seed=seed
                ):
                    print(chunk, end="", flush=True)
                    response_text += chunk
                
                print(f"\n{'='*40}")
                
                # Filter out think tags if present
                response_text = self._filter_think_tags(response_text)
                
                if debug:
                    print(f"[CONVERSATION] Step {i} Response Length: {len(response_text)} characters")
                
                # Add assistant response to conversation
                conversation_messages.append({"role": "assistant", "content": response_text})
                
                # Store final response
                final_response = response_text
            
            if debug:
                print(f"[CONVERSATION] Completed {len(user_messages)} steps")
                print(f"[CONVERSATION] Final response length: {len(final_response)} characters")
            
            return final_response
            
        except Exception as e:
            raise ModelProviderError(f"LM Studio multi-step conversation streaming failed: {e}") from e
