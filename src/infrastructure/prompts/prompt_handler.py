"""Prompt handler for managing savepoints and prompt execution."""

import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from domain.repositories.savepoint_repository import SavepointRepository
from domain.value_objects.model_config import ModelConfig
from application.interfaces.model_provider import ModelProvider
from .prompt_loader import PromptLoader
from domain.exceptions import StoryGenerationError


@dataclass
class PromptRequest:
    """Request object for prompt execution."""
    prompt_id: str
    variables: Optional[Dict[str, Any]] = None
    savepoint_id: Optional[str] = None
    prepend_message: Optional[str] = None
    model_config: Optional[ModelConfig] = None
    force_regenerate: bool = False
    system_message: Optional[str] = None
    seed: Optional[int] = None
    format_type: Optional[str] = None
    min_word_count: int = 1
    debug: bool = False
    stream: bool = False
    log_prompt_inputs: bool = False


@dataclass
class PromptResponse:
    """Response object for prompt execution."""
    content: str
    savepoint_id: Optional[str] = None
    was_cached: bool = False
    model_used: Optional[str] = None
    execution_time: Optional[float] = None


class PromptHandler:
    """Handler for managing prompt execution with savepoint support."""
    
    def __init__(
        self,
        model_provider: ModelProvider,
        prompt_loader: PromptLoader,
        savepoint_repo: Optional[SavepointRepository] = None
    ):
        self.model_provider = model_provider
        self.prompt_loader = prompt_loader
        self.savepoint_repo = savepoint_repo
    
    async def execute_prompt(self, request: PromptRequest) -> PromptResponse:
        """
        Execute a prompt with savepoint management.
        
        Args:
            request: PromptRequest containing all execution parameters
            
        Returns:
            PromptResponse with the generated content and metadata
        """
        import time
        start_time = time.time()
        
        # Check if we should use a savepoint
        if request.savepoint_id and self.savepoint_repo and not request.force_regenerate:
            # Check if savepoint exists
            if await self.savepoint_repo.has_savepoint(request.savepoint_id):
                cached_content = await self.savepoint_repo.load_savepoint(request.savepoint_id)
                if cached_content is not None:
                    execution_time = time.time() - start_time
                    return PromptResponse(
                        content=cached_content,
                        savepoint_id=request.savepoint_id,
                        was_cached=True,
                        execution_time=execution_time
                    )
        
        # Load and prepare the prompt
        try:
            prompt_content = self.prompt_loader.load_prompt(request.prompt_id, request.variables)
        except Exception as e:
            raise StoryGenerationError(f"Failed to load prompt '{request.prompt_id}': {e}")
        
        # Debug logging
        if request.debug:
            print(f"[PROMPT DEBUG] Executing prompt: {request.prompt_id}")
            if request.savepoint_id:
                print(f"[PROMPT DEBUG] Savepoint ID: {request.savepoint_id}")
            if request.model_config:
                print(f"[PROMPT DEBUG] Model: {request.model_config.name}")
        
        # Log prompt input if enabled
        if getattr(request, 'log_prompt_inputs', False):
            print(f"\n{'='*80}")
            print(f"[PROMPT INPUT] {request.prompt_id}")
            print(f"{'='*80}")
            print(prompt_content)
            print(f"{'='*80}\n")
        
        # Prepare messages
        messages = self._prepare_messages(prompt_content, request.prepend_message, request.system_message)

        print(f"Request: {request.prompt_id}")
        
        # Execute the prompt
        try:
            if request.model_config is None:
                raise StoryGenerationError("Model configuration is required for prompt execution")
            
            if request.stream:
                # Handle streaming with console output
                raw_response = await self._execute_prompt_with_streaming(
                    messages=messages,
                    model_config=request.model_config,
                    seed=request.seed,
                    format_type=request.format_type
                )
                # Extract thinking and content from the streaming response
                thinking_content, content = self._extract_thinking_and_content(raw_response)
            else:
                # Get the raw response to capture thinking
                raw_response = await self._get_raw_response(
                    messages=messages,
                    model_config=request.model_config,
                    seed=request.seed,
                    format_type=request.format_type,
                    min_word_count=request.min_word_count,
                    debug=request.debug,
                    stream=request.stream
                )
                
                # Extract thinking and content
                thinking_content, content = self._extract_thinking_and_content(raw_response)
        except Exception as e:
            raise StoryGenerationError(f"Failed to execute prompt '{request.prompt_id}': {e}")
        
        # Save to savepoint if requested
        if request.savepoint_id and self.savepoint_repo:
            try:
                # Create savepoint data with frontmatter
                savepoint_data = self._create_savepoint_data(
                    content=content,
                    thinking=thinking_content,
                    input_prompt=prompt_content,
                    prompt_id=request.prompt_id,
                    prepend_message=request.prepend_message,
                    system_message=request.system_message,
                    model_config=request.model_config,
                    seed=request.seed,
                    execution_time=time.time() - start_time
                )
                await self.savepoint_repo.save_savepoint(request.savepoint_id, savepoint_data)
            except Exception as e:
                # Log the error but don't fail the request
                print(f"Warning: Failed to save savepoint '{request.savepoint_id}': {e}")
        
        execution_time = time.time() - start_time
        
        return PromptResponse(
            content=content,
            savepoint_id=request.savepoint_id,
            was_cached=False,
            model_used=request.model_config.to_string() if request.model_config else None,
            execution_time=execution_time
        )
    
    async def execute_json_prompt(
        self, 
        request: PromptRequest, 
        required_attributes: List[str]
    ) -> Dict[str, Any]:
        """
        Execute a prompt that returns JSON with savepoint management.
        
        Args:
            request: PromptRequest containing all execution parameters
            required_attributes: List of required JSON attributes
            
        Returns:
            Dictionary containing the JSON response
        """
        import time
        start_time = time.time()
        
        # Check if we should use a savepoint
        if request.savepoint_id and self.savepoint_repo and not request.force_regenerate:
            # Check if savepoint exists
            if await self.savepoint_repo.has_savepoint(request.savepoint_id):
                cached_content = await self.savepoint_repo.load_savepoint(request.savepoint_id)
                if cached_content is not None:
                    return cached_content
        
        # Load and prepare the prompt
        try:
            prompt_content = self.prompt_loader.load_prompt(request.prompt_id, request.variables)
        except Exception as e:
            raise StoryGenerationError(f"Failed to load prompt '{request.prompt_id}': {e}")
        
        # Debug logging
        if request.debug:
            print(f"[PROMPT DEBUG] Executing JSON prompt: {request.prompt_id}")
            if request.savepoint_id:
                print(f"[PROMPT DEBUG] Savepoint ID: {request.savepoint_id}")
            if request.model_config:
                print(f"[PROMPT DEBUG] Model: {request.model_config.name}")
        
        # Prepare messages
        messages = self._prepare_messages(prompt_content, request.prepend_message, request.system_message)
        
        # Execute the prompt
        try:
            if request.model_config is None:
                raise StoryGenerationError("Model configuration is required for prompt execution")
            
            # Get the raw response to capture thinking
            raw_response = await self._get_raw_json_response(
                messages=messages,
                model_config=request.model_config,
                required_attributes=required_attributes,
                seed=request.seed,
                debug=request.debug
            )
            
            # Extract thinking and content
            thinking_content, content = self._extract_thinking_and_json_content(raw_response)
        except Exception as e:
            raise StoryGenerationError(f"Failed to execute JSON prompt '{request.prompt_id}': {e}")
        
        # Save to savepoint if requested
        if request.savepoint_id and self.savepoint_repo:
            try:
                # Create savepoint data with frontmatter
                savepoint_data = self._create_savepoint_data(
                    content=content,
                    thinking=thinking_content,
                    input_prompt=prompt_content,
                    prompt_id=request.prompt_id,
                    prepend_message=request.prepend_message,
                    system_message=request.system_message,
                    model_config=request.model_config,
                    seed=request.seed,
                    execution_time=time.time() - start_time
                )
                await self.savepoint_repo.save_savepoint(request.savepoint_id, savepoint_data)
            except Exception as e:
                # Log the error but don't fail the request
                print(f"Warning: Failed to save savepoint '{request.savepoint_id}': {e}")
        
        return content
    
    def _prepare_messages(
        self, 
        prompt_content: str, 
        prepend_message: Optional[str] = None,
        system_message: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Prepare messages for the model provider."""
        messages = []
        
        # Add system message if provided
        if system_message:
            user_content = f"{system_message}\n\n{prompt_content}"
        
        elif prepend_message:
            user_content = f"{prepend_message}\n\n{prompt_content}"
        else:
            user_content = prompt_content
        
        messages.append({"role": "user", "content": user_content})
        
        return messages
    
    async def check_savepoint_exists(self, savepoint_id: str) -> bool:
        """Check if a savepoint exists."""
        if not self.savepoint_repo:
            return False
        return await self.savepoint_repo.has_savepoint(savepoint_id)
    
    async def load_savepoint(self, savepoint_id: str) -> Optional[Any]:
        """Load a savepoint."""
        if not self.savepoint_repo:
            return None
        return await self.savepoint_repo.load_savepoint(savepoint_id)
    
    async def delete_savepoint(self, savepoint_id: str) -> bool:
        """Delete a savepoint."""
        if not self.savepoint_repo:
            return False
        return await self.savepoint_repo.delete_savepoint(savepoint_id)
    
    async def list_savepoints(self) -> Dict[str, Any]:
        """List all savepoints."""
        if not self.savepoint_repo:
            return {}
        return await self.savepoint_repo.list_savepoints()
    
    async def clear_all_savepoints(self) -> None:
        """Clear all savepoints."""
        if self.savepoint_repo:
            await self.savepoint_repo.clear_all_savepoints()
    
    def set_story_directory(self, story_name: str) -> None:
        """Set the story directory for savepoints."""
        if self.savepoint_repo and hasattr(self.savepoint_repo, 'set_story_directory'):
            self.savepoint_repo.set_story_directory(story_name)
    
    async def _execute_prompt_with_streaming(
        self,
        messages: List[Dict[str, str]],
        model_config: ModelConfig,
        seed: Optional[int] = None,
        format_type: Optional[str] = None
    ) -> str:
        """Execute prompt with streaming output to console."""
        full_response = ""
        buffer = ""
        in_thinking = False
        thinking_buffer = ""
        
        # print(f"Streaming prompt: {messages}")
        print(f"Model config: {model_config}")

        async for chunk in self.model_provider.stream_text(
            messages=messages,
            model_config=model_config,
            seed=seed,
            format_type=format_type
        ):
            # Add chunk to buffer
            buffer += chunk
            
            # Process buffer for complete tags
            while True:
                if not in_thinking:
                    # Look for start of think tag
                    think_start = buffer.find('<think>')
                    if think_start != -1:
                        # Print content before think tag
                        if think_start > 0:
                            content_before = buffer[:think_start]
                            print(content_before, end="", flush=True)
                        
                        # Remove content up to and including think tag start
                        buffer = buffer[think_start + 7:]  # 7 is len('<think>')
                        in_thinking = True
                        continue
                    else:
                        # No think tag found, print the buffer
                        if buffer:
                            print(buffer, end="", flush=True)
                            buffer = ""
                        break
                else:
                    # We're inside a think tag, look for end
                    think_end = buffer.find('</think>')
                    if think_end != -1:
                        # Collect thinking content
                        thinking_buffer += buffer[:think_end]
                        
                        # Display thinking content with visual distinction
                        print(f"\n[THINKING] {thinking_buffer}\n", end="", flush=True)
                        
                        # Remove content up to and including think tag end
                        buffer = buffer[think_end + 8:]  # 8 is len('</think>')
                        in_thinking = False
                        thinking_buffer = ""
                        continue
                    else:
                        # Think tag not complete, keep buffering
                        thinking_buffer += buffer
                        buffer = ""
                        break
            
            full_response += chunk
        
        print()  # New line after streaming
        
        return full_response
    
    async def _get_raw_response(
        self,
        messages: List[Dict[str, str]],
        model_config: ModelConfig,
        seed: Optional[int] = None,
        format_type: Optional[str] = None,
        min_word_count: int = 1,
        debug: bool = False,
        stream: bool = False
    ) -> str:
        """Get raw response from model provider to capture thinking."""
        # Always use non-streaming for raw response capture to get thinking
        # The stream parameter is ignored here since we want the full response with thinking
        return await self.model_provider.generate_text(
            messages=messages,
            model_config=model_config,
            seed=seed,
            format_type=format_type,
            min_word_count=min_word_count,
            debug=debug,
            stream=False  # Always use non-streaming for thinking capture
        )
    
    async def _get_raw_json_response(
        self,
        messages: List[Dict[str, str]],
        model_config: ModelConfig,
        required_attributes: List[str],
        seed: Optional[int] = None,
        debug: bool = False
    ) -> Dict[str, Any]:
        """Get raw JSON response from model provider to capture thinking."""
        # For now, we'll use the standard generate_json method
        # In the future, we could modify the model provider to return raw responses
        return await self.model_provider.generate_json(
            messages=messages,
            model_config=model_config,
            required_attributes=required_attributes,
            seed=seed,
            debug=debug
        )
    
    def _extract_thinking_and_content(self, raw_response: str) -> tuple[Optional[str], str]:
        """Extract thinking and content from raw response."""
        import re
        
        # Look for thinking content in <think> tags
        thinking_match = re.search(r'<think>(.*?)</think>', raw_response, re.DOTALL)
        if thinking_match:
            thinking_content = thinking_match.group(1).strip()
            # Remove thinking tags from the content
            content = re.sub(r'<think>.*?</think>', '', raw_response, flags=re.DOTALL).strip()
            return thinking_content, content
        
        # If no thinking tags found, return None for thinking and the full response as content
        return None, raw_response.strip()
    
    def _extract_thinking_and_json_content(self, raw_response: Dict[str, Any]) -> tuple[Optional[str], Dict[str, Any]]:
        """Extract thinking and JSON content from raw response."""
        # For JSON responses, we assume the thinking is not captured in the current implementation
        # This could be enhanced in the future if the model provider supports thinking for JSON
        return None, raw_response
    
    def _create_savepoint_data(
        self,
        content: Any,
        thinking: Optional[str],
        input_prompt: str,
        prompt_id: str,
        prepend_message: Optional[str],
        system_message: Optional[str],
        model_config: ModelConfig,
        seed: Optional[int],
        execution_time: float
    ) -> Dict[str, Any]:
        """Create savepoint data with frontmatter for metadata and body for content."""
        # Create frontmatter with metadata
        frontmatter = {
            "prompt_id": prompt_id,
            "input_prompt": input_prompt,
            "model_config": {
                "name": model_config.name,
                "provider": model_config.provider,
                "host": model_config.host,
                "parameters": model_config.parameters
            },
            "seed": seed,
            "execution_time": execution_time,
            "timestamp": __import__("datetime").datetime.now().isoformat()
        }
        
        # Add optional fields to frontmatter
        if thinking:
            frontmatter["thinking"] = thinking
        if prepend_message:
            frontmatter["prepend_message"] = prepend_message
        if system_message:
            frontmatter["system_message"] = system_message
        
        # Create the savepoint data structure
        savepoint_data = {
            "_frontmatter": frontmatter,
            "_body": content
        }
        
        return savepoint_data 