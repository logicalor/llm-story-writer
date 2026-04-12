"""llama.cpp model provider implementation."""

import asyncio
import json
import random
import re
import subprocess
import sys
from typing import List, Dict, Any, Optional, AsyncGenerator
from domain.value_objects.model_config import ModelConfig
from domain.exceptions import ModelProviderError
from application.interfaces.model_provider import ModelProvider


class LlamaCppProvider(ModelProvider):
    """llama.cpp model provider implementation."""
    
    def __init__(self, host: str = "127.0.0.1:8080", context_length: int = 16384, randomize_seed: bool = True):
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
        context_length = model_config.parameters.get('n_ctx', self.context_length)
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
    
    def _convert_messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Convert chat messages to a single prompt string for llama.cpp."""
        prompt = ""
        for message in messages:
            role = message.get('role', '')
            content = message.get('content', '')
            
            if role == 'system':
                prompt += f"System: {content}\n\n"
            elif role == 'user':
                prompt += f"User: {content}\n\n"
            elif role == 'assistant':
                prompt += f"Assistant: {content}\n\n"
            else:
                prompt += f"{role.capitalize()}: {content}\n\n"
        
        # Add the final assistant prompt
        prompt += "Assistant: "
        return prompt
    
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
        """Generate text using llama.cpp."""
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
            raise ModelProviderError(f"llama.cpp generation failed: {e}") from e
    
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
            import requests
            
            # Display debug prompt if enabled
            if debug:
                self._display_debug_prompt(messages, model_config)
            
            # Log prompt statistics
            self._log_prompt_stats(messages, model_config)
            
            # Convert messages to prompt format
            prompt = self._convert_messages_to_prompt(messages)
            
            # Prepare request payload
            payload = self._prepare_payload(model_config, seed, format_type)
            payload['prompt'] = prompt
            
            # Output model and options details
            print(f"\n[CHAT REQUEST] Model: {model_config.name}")
            print(f"[CHAT REQUEST] Provider: {model_config.provider}")
            if model_config.host:
                print(f"[CHAT REQUEST] Host: {model_config.host}")
            print(f"[CHAT REQUEST] Options: {payload}")
            print(f"[CHAT REQUEST] Format: {format_type or 'text'}")
            print(f"[CHAT REQUEST] Seed: {seed}")
            print(f"[CHAT REQUEST] Min word count: {min_word_count}")
            print()
            
            # Make request to llama.cpp server
            host = model_config.host or self.host
            url = f"http://{host}/completion"
            
            response = await asyncio.to_thread(
                requests.post,
                url,
                json=payload,
                timeout=300  # 5 minute timeout
            )
            
            if response.status_code != 200:
                raise ModelProviderError(f"llama.cpp API error: {response.status_code} - {response.text}")
            
            response_data = response.json()
            response_text = response_data.get('content', '')
            
            # Filter out think tags if present
            response_text = self._filter_think_tags(response_text)
            
            # Ensure minimum word count
            word_count = len(response_text.split())
            if word_count < min_word_count:
                # Retry with more specific prompt
                messages.append({"role": "assistant", "content": response_text})
                messages.append({"role": "user", "content": f"Please continue and expand on this response to reach at least {min_word_count} words."})
                
                prompt = self._convert_messages_to_prompt(messages)
                payload['prompt'] = prompt
                
                response = await asyncio.to_thread(
                    requests.post,
                    url,
                    json=payload,
                    timeout=300
                )
                
                if response.status_code != 200:
                    raise ModelProviderError(f"llama.cpp API error on continuation: {response.status_code} - {response.text}")
                
                response_data = response.json()
                response_text = response_data.get('content', '')
                response_text = self._filter_think_tags(response_text)
            
            return response_text
            
        except Exception as e:
            raise ModelProviderError(f"llama.cpp generation failed: {e}") from e
    
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
        """Generate JSON response using llama.cpp."""
        try:
            # Display debug prompt if enabled
            if debug:
                self._display_debug_prompt(messages, model_config)
                print(f"[DEBUG] Generating JSON response using {model_config.name}...")
                print(f"[DEBUG] Required attributes: {required_attributes}")
            
            # Log prompt statistics
            self._log_prompt_stats(messages, model_config)
            
            # Add JSON formatting instruction to the last user message
            json_messages = messages.copy()
            if json_messages and json_messages[-1]['role'] == 'user':
                json_messages[-1]['content'] += f"\n\nPlease respond with valid JSON containing the following attributes: {', '.join(required_attributes)}"
            
            # Convert messages to prompt format
            prompt = self._convert_messages_to_prompt(json_messages)
            
            # Prepare request payload with JSON formatting
            payload = self._prepare_payload(model_config, seed, "json")
            payload['prompt'] = prompt
            
            # Make request to llama.cpp server
            host = model_config.host or self.host
            url = f"http://{host}/completion"
            
            response = await asyncio.to_thread(
                requests.post,
                url,
                json=payload,
                timeout=300
            )
            
            if response.status_code != 200:
                raise ModelProviderError(f"llama.cpp API error: {response.status_code} - {response.text}")
            
            response_data = response.json()
            response_text = response_data.get('content', '')
            
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
            raise ModelProviderError(f"llama.cpp JSON generation failed: {e}") from e
    
    async def stream_text(
        self,
        messages: List[Dict[str, str]],
        model_config: ModelConfig,
        seed: Optional[int] = None,
        format_type: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Stream text generation using llama.cpp."""
        try:
            import requests
            
            # Log prompt statistics
            self._log_prompt_stats(messages, model_config)
            
            # Convert messages to prompt format
            prompt = self._convert_messages_to_prompt(messages)
            
            # Prepare request payload
            payload = self._prepare_payload(model_config, seed, format_type)
            payload['prompt'] = prompt
            payload['stream'] = True
            
            # Output model and options details
            print(f"\n[CHAT REQUEST] Model: {model_config.name}")
            print(f"[CHAT REQUEST] Provider: {model_config.provider}")
            if model_config.host:
                print(f"[CHAT REQUEST] Host: {model_config.host}")
            print(f"[CHAT REQUEST] Options: {payload}")
            print(f"[CHAT REQUEST] Format: {format_type or 'text'}")
            print(f"[CHAT REQUEST] Seed: {seed}")
            print(f"[CHAT REQUEST] Mode: streaming")
            print()
            
            # Make streaming request to llama.cpp server
            host = model_config.host or self.host
            url = f"http://{host}/completion"
            
            response = await asyncio.to_thread(
                requests.post,
                url,
                json=payload,
                timeout=300,
                stream=True
            )
            
            if response.status_code != 200:
                raise ModelProviderError(f"llama.cpp API error: {response.status_code} - {response.text}")
            
            # Process streaming response
            for line in response.iter_lines():
                if line:
                    try:
                        chunk_data = json.loads(line.decode('utf-8'))
                        if 'content' in chunk_data:
                            content = chunk_data['content']
                            yield content
                    except json.JSONDecodeError:
                        # Skip malformed JSON lines
                        continue
                    
        except Exception as e:
            raise ModelProviderError(f"llama.cpp streaming failed: {e}") from e
    
    async def is_model_available(self, model_config: ModelConfig) -> bool:
        """Check if a model is available in llama.cpp."""
        try:
            import requests
            
            host = model_config.host or self.host
            url = f"http://{host}/models"
            
            response = await asyncio.to_thread(
                requests.get,
                url,
                timeout=10
            )
            
            if response.status_code == 200:
                models_data = response.json()
                # Check if the model name is in the available models
                available_models = models_data.get('models', [])
                return any(model.get('name', '').startswith(model_config.name) for model in available_models)
            
            return False
            
        except Exception:
            return False
    
    async def download_model(self, model_config: ModelConfig) -> None:
        """Download a model in llama.cpp."""
        # llama.cpp models are typically downloaded manually or through other tools
        # This method provides a placeholder for consistency with the interface
        print(f"llama.cpp models are typically downloaded manually or through other tools.")
        print(f"Please ensure the model {model_config.name} is available at {model_config.host or self.host}")
        print(f"Refer to llama.cpp documentation for model download instructions.")
    
    async def get_supported_providers(self) -> List[str]:
        """Get list of supported providers."""
        return ["llama_cpp"]
    
    def _prepare_payload(
        self,
        model_config: ModelConfig,
        seed: Optional[int] = None,
        format_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Prepare payload for llama.cpp API call."""
        payload = model_config.parameters.copy()
        
        # Set context length from infrastructure config if not specified
        if 'n_ctx' not in payload:
            payload['n_ctx'] = self.context_length
        # If n_ctx is specified but exceeds infrastructure limit, cap it
        elif payload['n_ctx'] > self.context_length:
            print(f"[LLAMA.CPP] Warning: Requested n_ctx {payload['n_ctx']} exceeds infrastructure limit {self.context_length}, capping to {self.context_length}")
            payload['n_ctx'] = self.context_length
        
        # Set seed if provided, with conditional randomness
        if seed is not None:
            # Check if we should randomize the seed
            should_randomize = self.randomize_seed and not model_config.parameters.get('static_seed', False)
            
            if should_randomize:
                # Add random offset to ensure variety in generation
                random_offset = random.randint(1, 10000)
                payload['seed'] = seed + random_offset
                print(f"[LLAMA.CPP] Seed randomized: {seed} + {random_offset} = {payload['seed']}")
            else:
                # Use exact seed without randomization
                payload['seed'] = seed
                print(f"[LLAMA.CPP] Using static seed: {seed}")
        
        # Set temperature for JSON responses
        if format_type == "json":
            if 'temperature' not in payload:
                payload['temperature'] = 0
        
        # Set default values for common parameters
        if 'temperature' not in payload:
            payload['temperature'] = 0.7
        if 'top_p' not in payload:
            payload['top_p'] = 0.9
        if 'top_k' not in payload:
            payload['top_k'] = 40
        if 'repeat_penalty' not in payload:
            payload['repeat_penalty'] = 1.1
        
        # Log context length configuration for debugging
        if 'n_ctx' in payload:
            print(f"[LLAMA.CPP] Context length: {payload['n_ctx']} (from model config)")
        else:
            print(f"[LLAMA.CPP] Context length: {payload['n_ctx']} (from infrastructure default)")
        
        return payload
    
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
            raise ModelProviderError(f"llama.cpp multi-step conversation failed: {e}") from e
    
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
            import requests
            
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
                
                # Convert messages to prompt format
                prompt = self._convert_messages_to_prompt(conversation_messages)
                
                # Prepare request payload
                payload = self._prepare_payload(model_config, seed, None)
                payload['prompt'] = prompt
                
                # Make request to llama.cpp server
                host = model_config.host or self.host
                url = f"http://{host}/completion"
                
                response = await asyncio.to_thread(
                    requests.post,
                    url,
                    json=payload,
                    timeout=300
                )
                
                if response.status_code != 200:
                    raise ModelProviderError(f"llama.cpp API error: {response.status_code} - {response.text}")
                
                response_data = response.json()
                response_text = response_data.get('content', '')
                
                # Filter out think tags
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
            raise ModelProviderError(f"llama.cpp multi-step conversation failed: {e}") from e
    
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
                
                # Filter out think tags
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
            raise ModelProviderError(f"llama.cpp multi-step conversation streaming failed: {e}") from e
