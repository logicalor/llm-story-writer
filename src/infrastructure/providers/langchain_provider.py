"""LangChain model provider implementation."""

import asyncio
import json
import random
import re
from typing import List, Dict, Any, Optional, AsyncGenerator
from domain.value_objects.model_config import ModelConfig
from domain.exceptions import ModelProviderError
from application.interfaces.model_provider import ModelProvider


class LangChainProvider(ModelProvider):
    """LangChain model provider implementation."""
    
    def __init__(self, api_keys: Optional[Dict[str, str]] = None):
        self.api_keys = api_keys or {}
        self.clients = {}
        self._ensure_langchain_installed()
    
    def _ensure_langchain_installed(self):
        """Ensure langchain packages are installed."""
        try:
            import langchain
            import langchain_openai
            import langchain_anthropic
            import langchain_community
        except ImportError:
            print("LangChain packages not found. Installing...")
            import subprocess
            import sys
            subprocess.check_call([sys.executable, "-m", "pip", "install", 
                                 "langchain", "langchain-openai", "langchain-anthropic", "langchain-community"])
            import langchain
            import langchain_openai
            import langchain_anthropic
            import langchain_community
    
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
        context_length = model_config.parameters.get('max_tokens', 16384)
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
        """Generate text using LangChain."""
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
            raise ModelProviderError(f"LangChain generation failed: {e}") from e
    
    async def generate_multistep_conversation(
        self,
        user_messages: List[str],
        model_config: ModelConfig,
        system_message: Optional[str] = None,
        seed: Optional[int] = None,
        debug: bool = False
    ) -> str:
        """Generate text through a multi-step conversation with memory."""
        try:
            llm = await self._get_llm(model_config)
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
            conversation_memory = self._create_conversation_memory()
            
            # Add system message if provided
            if system_message:
                conversation_memory.chat_memory.add_message(
                    self._create_system_message(system_message)
                )
            
            # Process each user message sequentially
            final_response = ""
            for i, user_message in enumerate(user_messages, 1):
                if debug:
                    print(f"[CONVERSATION] Step {i}/{len(user_messages)}: Processing user message")
                    print(f"[CONVERSATION] User: {user_message[:100]}{'...' if len(user_message) > 100 else ''}")
                
                # Add user message to memory
                conversation_memory.chat_memory.add_user_message(user_message)
                
                # Get conversation history
                conversation_history = conversation_memory.load_memory_variables({})
                messages = conversation_history.get("history", [])
                
                # Generate response
                response = await asyncio.to_thread(
                    llm.invoke,
                    messages
                )
                
                response_text = response.content if hasattr(response, 'content') else str(response)
                
                # Filter out think tags if present
                response_text = self._filter_think_tags(response_text)
                
                if debug:
                    print(f"[CONVERSATION] Step {i} Response: {response_text[:100]}{'...' if len(response_text) > 100 else ''}")
                
                # Add assistant response to memory
                conversation_memory.chat_memory.add_ai_message(response_text)
                
                # Store final response
                final_response = response_text
            
            if debug:
                print(f"[CONVERSATION] Completed {len(user_messages)} steps")
                print(f"[CONVERSATION] Final response length: {len(final_response)} characters")
            
            return final_response
            
        except Exception as e:
            raise ModelProviderError(f"LangChain multi-step conversation failed: {e}") from e
    
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
            llm = await self._get_llm(model_config)
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
            
            # Convert messages to LangChain format
            langchain_messages = self._convert_messages_to_langchain(messages)
            
            # Generate response
            response = await asyncio.to_thread(
                llm.invoke,
                langchain_messages
            )
            
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Filter out think tags if present
            response_text = self._filter_think_tags(response_text)
            
            # Ensure minimum word count
            word_count = len(response_text.split())
            if word_count < min_word_count:
                # Retry with more specific prompt
                messages.append({"role": "assistant", "content": response_text})
                messages.append({"role": "user", "content": f"Please continue and expand on this response to reach at least {min_word_count} words."})
                
                langchain_messages = self._convert_messages_to_langchain(messages)
                response = await asyncio.to_thread(
                    llm.invoke,
                    langchain_messages
                )
                
                response_text = response.content if hasattr(response, 'content') else str(response)
                
                # Filter think tags from the continuation as well
                response_text = self._filter_think_tags(response_text)
            
            return response_text
            
        except Exception as e:
            raise ModelProviderError(f"LangChain generation failed: {e}") from e
    
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
        """Generate JSON response using LangChain."""
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
            raise ModelProviderError(f"LangChain JSON generation failed: {e}") from e
    
    async def stream_text(
        self,
        messages: List[Dict[str, str]],
        model_config: ModelConfig,
        seed: Optional[int] = None,
        format_type: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Stream text generation using LangChain."""
        try:
            llm = await self._get_llm(model_config)
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
            
            # Convert messages to LangChain format
            langchain_messages = self._convert_messages_to_langchain(messages)
            
            # Stream response
            async for chunk in self._stream_langchain_response(llm, langchain_messages):
                yield chunk
                    
        except Exception as e:
            raise ModelProviderError(f"LangChain streaming failed: {e}") from e
    
    async def is_model_available(self, model_config: ModelConfig) -> bool:
        """Check if a model is available through LangChain."""
        try:
            # Try to create the LLM to check availability
            await self._get_llm(model_config)
            return True
        except Exception:
            return False
    
    async def download_model(self, model_config: ModelConfig) -> None:
        """Download a model through LangChain."""
        # LangChain handles model downloads through the underlying providers
        print(f"LangChain handles model downloads through the underlying providers.")
        print(f"Please ensure the model '{model_config.name}' is available through the configured provider.")
    
    async def get_supported_providers(self) -> List[str]:
        """Get list of supported providers."""
        return ["langchain"]
    
    async def _get_llm(self, model_config: ModelConfig):
        """Get or create LangChain LLM instance."""
        if model_config.name not in self.clients:
            llm = await self._create_langchain_llm(model_config)
            self.clients[model_config.name] = llm
        
        return self.clients[model_config.name]
    
    async def _create_langchain_llm(self, model_config: ModelConfig):
        """Create a LangChain LLM instance based on the model configuration."""
        provider = model_config.provider.lower()
        model_name = model_config.name
        parameters = model_config.parameters.copy()
        
        # Set API keys from environment or config
        api_key = self._get_api_key(provider)
        
        if provider == "openai":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=model_name,
                openai_api_key=api_key,
                **parameters
            )
        
        elif provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model=model_name,
                anthropic_api_key=api_key,
                **parameters
            )
        
        elif provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                **parameters
            )
        
        elif provider == "ollama":
            from langchain_community.llms import Ollama
            host = model_config.host or "http://localhost:11434"
            return Ollama(
                model=model_name,
                base_url=host,
                **parameters
            )
        
        elif provider == "lm_studio":
            from langchain_openai import ChatOpenAI
            host = model_config.host or "http://localhost:1234"
            return ChatOpenAI(
                model=model_name,
                openai_api_base=host,
                openai_api_key="dummy",  # LM Studio doesn't require real API key
                **parameters
            )
        
        elif provider == "huggingface":
            from langchain_community.llms import HuggingFaceEndpoint
            return HuggingFaceEndpoint(
                repo_id=model_name,
                huggingfacehub_api_token=api_key,
                **parameters
            )
        
        else:
            # Try to use a generic OpenAI-compatible endpoint
            from langchain_openai import ChatOpenAI
            host = model_config.host or "http://localhost:8000"
            return ChatOpenAI(
                model=model_name,
                openai_api_base=host,
                openai_api_key=api_key or "dummy",
                **parameters
            )
    
    def _get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for the specified provider."""
        # Check config first
        if provider in self.api_keys:
            return self.api_keys[provider]
        
        # Check environment variables
        import os
        provider_upper = provider.upper()
        
        if provider == "openai":
            return os.getenv("OPENAI_API_KEY")
        elif provider == "anthropic":
            return os.getenv("ANTHROPIC_API_KEY")
        elif provider == "google":
            return os.getenv("GOOGLE_API_KEY")
        elif provider == "huggingface":
            return os.getenv("HUGGINGFACE_API_KEY")
        
        return None
    
    def _convert_messages_to_langchain(self, messages: List[Dict[str, str]]):
        """Convert messages to LangChain format."""
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
        
        langchain_messages = []
        for message in messages:
            role = message.get('role', '')
            content = message.get('content', '')
            
            if role == 'user':
                langchain_messages.append(HumanMessage(content=content))
            elif role == 'assistant':
                langchain_messages.append(AIMessage(content=content))
            elif role == 'system':
                langchain_messages.append(SystemMessage(content=content))
            else:
                # Default to human message for unknown roles
                langchain_messages.append(HumanMessage(content=content))
        
        return langchain_messages
    
    async def _stream_langchain_response(self, llm, messages):
        """Stream response from LangChain LLM."""
        try:
            # Use streaming if available
            if hasattr(llm, 'astream'):
                async for chunk in llm.astream(messages):
                    if hasattr(chunk, 'content') and chunk.content:
                        yield chunk.content
            else:
                # Fallback to non-streaming
                response = await asyncio.to_thread(llm.invoke, messages)
                content = response.content if hasattr(response, 'content') else str(response)
                yield content
        except Exception as e:
            print(f"Streaming failed, falling back to non-streaming: {e}")
            response = await asyncio.to_thread(llm.invoke, messages)
            content = response.content if hasattr(response, 'content') else str(response)
            yield content
    
    def _prepare_options(
        self,
        model_config: ModelConfig,
        seed: Optional[int] = None,
        format_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Prepare options for LangChain API call."""
        options = model_config.parameters.copy()
        
        # Set default context length if not specified
        if 'max_tokens' not in options:
            options['max_tokens'] = 16384
        
        # Set seed if provided, with automatic randomness
        if seed is not None:
            # Add random offset to ensure variety in generation
            random_offset = random.randint(1, 10000)
            options['seed'] = seed + random_offset
        
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
            llm = await self._get_llm(model_config)
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
            
            # Convert messages to LangChain format
            langchain_messages = self._convert_messages_to_langchain(messages)
            
            # Generate response
            response = await asyncio.to_thread(
                llm.invoke,
                langchain_messages
            )
            
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Filter out think tags if present
            response_text = self._filter_think_tags(response_text)
            
            # Ensure minimum word count
            word_count = len(response_text.split())
            if word_count < min_word_count:
                # Retry with more specific prompt
                messages.append({"role": "assistant", "content": response_text})
                messages.append({"role": "user", "content": f"Please continue and expand on this response to reach at least {min_word_count} words."})
                
                langchain_messages = self._convert_messages_to_langchain(messages)
                response = await asyncio.to_thread(
                    llm.invoke,
                    langchain_messages
                )
                
                response_text = response.content if hasattr(response, 'content') else str(response)
                
                # Filter think tags from the continuation as well
                response_text = self._filter_think_tags(response_text)
            
            return response_text
            
        except Exception as e:
            raise ModelProviderError(f"LangChain generation failed: {e}") from e
    
    def _create_conversation_memory(self):
        """Create a conversation memory instance for maintaining context."""
        try:
            from langchain.memory import ConversationBufferMemory
            from langchain_core.messages import SystemMessage
            
            # Create memory with system message support
            memory = ConversationBufferMemory(
                memory_key="history",
                return_messages=True,
                input_key="input"
            )
            
            return memory
            
        except ImportError:
            # Fallback if langchain.memory is not available
            from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
            
            # Create a simple memory implementation
            class SimpleMemory:
                def __init__(self):
                    self.chat_memory = SimpleChatMemory()
                
                def load_memory_variables(self, inputs):
                    return {"history": self.chat_memory.messages}
            
            class SimpleChatMemory:
                def __init__(self):
                    self.messages = []
                
                def add_message(self, message):
                    self.messages.append(message)
                
                def add_user_message(self, message):
                    self.messages.append(HumanMessage(content=message))
                
                def add_ai_message(self, message):
                    self.messages.append(AIMessage(content=message))
            
            return SimpleMemory()
    
    def _create_system_message(self, content: str):
        """Create a system message for the conversation."""
        try:
            from langchain_core.messages import SystemMessage
            return SystemMessage(content=content)
        except ImportError:
            # Fallback implementation
            class SimpleSystemMessage:
                def __init__(self, content):
                    self.content = content
                    self.type = "system"
            
            return SimpleSystemMessage(content)
