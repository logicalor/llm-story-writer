"""Simple wrapper functions for prompt execution with savepoint management."""

from typing import Dict, Any, Optional
from domain.value_objects.model_config import ModelConfig
from .prompt_handler import PromptHandler, PromptRequest, PromptResponse

def extract_boxed_solution(text: str) -> Optional[str]:
    """
    Extracts the content of the last `\boxed{}` in a given LaTeX-style text.
    Args:
        text (str): The input string containing LaTeX-style content.
    Returns:
        Optional[str]: The extracted content inside the last `\boxed{}` if found 
        and properly matched, otherwise `None`.
    Example:
        >>> extract_boxed_solution("The result is \\boxed{42}.")
        '42'
        >>> extract_boxed_solution("Unmatched \\boxed{42")
        None
    """
    try:
        start_index = text.rindex("\\boxed{")
        content_start = start_index + 7
        bracket_count = 1
        current_pos = content_start

        while bracket_count > 0 and current_pos < len(text):
            if text[current_pos] == "{":
                bracket_count += 1
            elif text[current_pos] == "}":
                bracket_count -= 1
            current_pos += 1

        if bracket_count == 0:
            content = text[content_start : current_pos - 1].strip()
            # Unescape common escape sequences
            content = content.replace("\\n", "\n")
            content = content.replace("\\t", "\t")
            content = content.replace("\\r", "\r")
            content = content.replace("\\\"", "\"")
            content = content.replace("\\'", "'")
            content = content.replace("\\\\", "\\")
            return content
        else:
            print("Error: Unmatched brackets in the text")
            return None

    except ValueError:
        print("No boxed solution found in the text")
        return None
    except Exception as e:
        print(f"Error processing text: {str(e)}")
        return None


def extract_output_tags(text: str) -> Optional[str]:
    """
    Extracts the content of the last `<output>...</output>` tags in a given text.
    Handles unclosed tags gracefully by extracting content up to the end of text.
    Args:
        text (str): The input string containing output tags.
    Returns:
        Optional[str]: The extracted content inside the last `<output>` tags if found, 
        or content from unclosed tag to end of text, otherwise `None`.
    Example:
        >>> extract_output_tags("Here is the result: <output>42</output>")
        '42'
        >>> extract_output_tags("Unmatched <output>42")
        '42'
    """
    if text is None:
        return None
        
    try:
        start_index = text.rindex("<output>")
        content_start = start_index + 8  # Length of "<output>"
        
        # Try to find the closing tag
        try:
            end_index = text.rindex("</output>")
            if end_index > start_index:
                # Found properly closed tags
                content = text[content_start:end_index].strip()
                return content
            else:
                # Closing tag is before opening tag, treat as unclosed
                content = text[content_start:].strip()
                print(f"⚠️ Warning: Found unclosed <output> tag, extracting content to end of text")
                return content
        except ValueError:
            # No closing tag found, extract to end of text
            content = text[content_start:].strip()
            print(f"⚠️ Warning: Found unclosed <output> tag, extracting content to end of text")
            return content

    except ValueError:
        return None
    except Exception as e:
        print(f"Error processing output tags: {str(e)}")
        return None


def validate_and_parse_output(text: str, skip_validation: bool = False) -> tuple[str, bool]:
    """
    Validates and parses output content based on <output> tags.
    
    Args:
        text (str): The raw output text to validate and parse
        skip_validation (bool): If True, return raw text without validation
        
    Returns:
        tuple[str, bool]: (parsed_content, needs_retry)
            - parsed_content: The extracted content or raw text
            - needs_retry: True if validation failed and retry is needed
    """
    if skip_validation:
        return text, False
    
    # Check if output tags are present
    if "<output>" in text:
        parsed_content = extract_output_tags(text)
        if parsed_content is not None:
            return parsed_content, False
        else:
            print("⚠️ Warning: Output tags found but content extraction failed")
            return text, False
    
    # No output tags found - this is a parsing error
    print("❌ Parsing Error: Expected output wrapped in <output> tags but none found")
    print("   Raw output preview:", text[:200] + "..." if len(text) > 200 else text)
    return text, True

async def execute_prompt_with_savepoint(
    handler: PromptHandler,
    prompt_id: str,
    variables: Optional[Dict[str, Any]] = None,
    savepoint_id: Optional[str] = None,
    prepend_message: Optional[str] = None,
    model_config: Optional[ModelConfig] = None,
    force_regenerate: bool = False,
    system_message: Optional[str] = None,
    expect_json: bool = False,
    json_schema: Optional[Dict[str, Any]] = None,
    use_boxed_solution: bool = False,
    skip_validation: bool = False,
    **kwargs
) -> PromptResponse:
    """
    Simple wrapper function for prompt execution with savepoint management.
    
    Args:
        handler: PromptHandler instance
        prompt_id: ID of the prompt to execute
        variables: Variables to substitute in the prompt
        savepoint_id: ID for the savepoint (optional)
        prepend_message: Optional message to prepend to the prompt
        model_config: Model configuration to use
        force_regenerate: Force regeneration even if savepoint exists
        system_message: Optional system message
        expect_json: Whether to expect and parse JSON response
        json_schema: JSON schema for parsing response (required if expect_json=True)
        **kwargs: Additional arguments passed to PromptRequest
        
    Returns:
        PromptResponse with the generated content and metadata
    """
    import time
    
    start_time = time.time()
    
    request = PromptRequest(
        prompt_id=prompt_id,
        variables=variables,
        savepoint_id=savepoint_id,
        prepend_message=prepend_message,
        model_config=model_config,
        force_regenerate=force_regenerate,
        system_message=system_message,
        expect_json=expect_json,
        json_schema=json_schema,
        **kwargs
    )
    
    response = await handler.execute_prompt(request)
    
    # Skip validation and parsing if content comes from a savepoint (already parsed)
    if response.was_cached:
        parsed_content = response.content
        print(f"📋 Using cached content from savepoint '{savepoint_id}' - skipping validation/parsing")
    else:
        # Apply output validation and parsing for newly generated content
        parsed_content, needs_retry = validate_and_parse_output(response.content, skip_validation)
        if needs_retry:
            print(f"🔄 Retrying prompt '{prompt_id}' due to missing output tags...")
            # Retry the prompt once
            retry_response = await handler.execute_prompt(request)
            parsed_content, needs_retry = validate_and_parse_output(retry_response.content, skip_validation)
            if needs_retry:
                print(f"⚠️ Warning: Retry failed for prompt '{prompt_id}', using raw output")
                parsed_content = retry_response.content
            else:
                response = retry_response
    
    # Apply boxed solution extraction if requested
    if use_boxed_solution:
        boxed_solution = extract_boxed_solution(parsed_content)
        if boxed_solution is not None:
            parsed_content = boxed_solution
    
    # Update response content with parsed/validated content
    response.content = parsed_content
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Log the timing
    model_name = model_config.name if model_config else "unknown"
    savepoint_info = f" (savepoint: {savepoint_id})" if savepoint_id else ""
    print(f"[PROMPT TIMING] {prompt_id} | Model: {model_name} | Duration: {duration:.2f}s{savepoint_info}")
    
    return response


async def execute_prompt(
    handler: PromptHandler,
    prompt_id: str,
    variables: Optional[Dict[str, Any]] = None,
    prepend_message: Optional[str] = None,
    model_config: Optional[ModelConfig] = None,
    system_message: Optional[str] = None,
    use_boxed_solution: bool = False,
    skip_validation: bool = False,
    **kwargs
) -> PromptResponse:
    """
    Simple wrapper function for prompt execution without savepoint management.
    
    Args:
        handler: PromptHandler instance
        prompt_id: ID of the prompt to execute
        variables: Variables to substitute in the prompt
        prepend_message: Optional message to prepend to the prompt
        model_config: Model configuration to use
        system_message: Optional system message
        **kwargs: Additional arguments passed to PromptRequest
        
    Returns:
        PromptResponse with the generated content and metadata
    """
    import time
    
    start_time = time.time()
    
    request = PromptRequest(
        prompt_id=prompt_id,
        variables=variables,
        savepoint_id=None,  # No savepoint management
        prepend_message=prepend_message,
        model_config=model_config,
        system_message=system_message,
        **kwargs
    )
    
    response = await handler.execute_prompt(request)
    
    # Skip validation and parsing if content comes from a savepoint (already parsed)
    if response.was_cached:
        parsed_content = response.content
        print(f"📋 Using cached content from savepoint - skipping validation/parsing")
    else:
        # Apply output validation and parsing for newly generated content
        parsed_content, needs_retry = validate_and_parse_output(response.content, skip_validation)
        if needs_retry:
            print(f"🔄 Retrying prompt '{prompt_id}' due to missing output tags...")
            # Retry the prompt once
            retry_response = await handler.execute_prompt(request)
            parsed_content, needs_retry = validate_and_parse_output(retry_response.content, skip_validation)
            if needs_retry:
                print(f"⚠️ Warning: Retry failed for prompt '{prompt_id}', using raw output")
                parsed_content = retry_response.content
            else:
                response = retry_response
    
    # Apply boxed solution extraction if requested
    if use_boxed_solution:
        boxed_solution = extract_boxed_solution(parsed_content)
        if boxed_solution is not None:
            parsed_content = boxed_solution
    
    # Update response content with parsed/validated content
    response.content = parsed_content
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Log the timing
    model_name = model_config.name if model_config else "unknown"
    print(f"[PROMPT TIMING] {prompt_id} | Model: {model_name} | Duration: {duration:.2f}s")
    
    return response


async def execute_messages_with_savepoint(
    handler: PromptHandler,
    conversation_history: list,
    savepoint_id: Optional[str] = None,
    model_config: Optional[ModelConfig] = None,
    force_regenerate: bool = False,
    expect_json: bool = False,
    json_schema: Optional[Dict[str, Any]] = None,
    use_boxed_solution: bool = False,
    skip_validation: bool = False,
    **kwargs
) -> PromptResponse:
    """
    Execute a conversation with a custom conversation history and savepoint management.
    
    This method allows you to define the complete conversation history including both
    user and assistant messages, and sends the final user message to get a response.
    
    Args:
        handler: PromptHandler instance
        conversation_history: List of conversation messages in format [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ...]
        savepoint_id: ID for the savepoint (optional)
        model_config: Model configuration to use
        force_regenerate: Force regeneration even if savepoint exists
        expect_json: Whether to expect and parse JSON response
        json_schema: JSON schema for parsing response (required if expect_json=True)
        **kwargs: Additional arguments passed to PromptRequest
        
    Returns:
        PromptResponse with the generated content and metadata
    """
    import time
    
    start_time = time.time()
    
    # Check if we should use a savepoint
    if savepoint_id and handler.savepoint_repo and not force_regenerate:
        if await handler.savepoint_repo.has_savepoint(savepoint_id):
            cached_content = await handler.savepoint_repo.load_savepoint(savepoint_id)
            if cached_content is not None:
                # Handle JSON parsing if requested
                json_parsed = False
                json_errors = None
                
                if expect_json and json_schema:
                    try:
                        from llm_output_parser import parse_json
                        parsed_content = parse_json(cached_content, strict=False)
                        
                        if parsed_content is not None:
                            cached_content = json.dumps(parsed_content, indent=2)
                            json_parsed = True
                        else:
                            json_errors = "Failed to extract valid JSON from cached response"
                    except Exception as e:
                        json_errors = f"JSON parsing error: {e}"
                
                end_time = time.time()
                duration = end_time - start_time
                
                model_name = model_config.name if model_config else "unknown"
                print(f"[MESSAGES TIMING] {len(conversation_history)} messages | Model: {model_name} | Duration: {duration:.2f}s (cached)")
                
                return PromptResponse(
                    content=cached_content,
                    savepoint_id=savepoint_id,
                    was_cached=True,
                    model_used=model_name,
                    execution_time=duration,
                    json_parsed=json_parsed,
                    json_errors=json_errors
                )
    
    # Execute the conversation with custom history
    try:
        # Extract parameters from kwargs
        seed = kwargs.get('seed')
        debug = kwargs.get('debug', False)
        stream = kwargs.get('stream', False)
        
        # Use the model provider's text generation functionality with custom conversation history
        response_content = await handler.model_provider.generate_text(
            messages=conversation_history,
            model_config=model_config,
            seed=seed,
            debug=debug,
            stream=stream
        )
        
        # For conversation execution, we always need to validate and parse since it's not using savepoints
        # Apply output validation and parsing
        parsed_content, needs_retry = validate_and_parse_output(response_content, skip_validation)
        if needs_retry:
            print(f"🔄 Retrying conversation due to missing output tags...")
            # Retry the conversation once
            retry_content = await handler.model_provider.generate_text(
                messages=conversation_history,
                model_config=model_config,
                seed=seed,
                debug=debug,
                stream=stream
            )
            parsed_content, needs_retry = validate_and_parse_output(retry_content, skip_validation)
            if needs_retry:
                print(f"⚠️ Warning: Retry failed for conversation, using raw output")
                parsed_content = retry_content
            else:
                response_content = retry_content
        
        # Apply boxed solution extraction if requested
        if use_boxed_solution:
            boxed_solution = extract_boxed_solution(parsed_content)
            if boxed_solution is not None:
                parsed_content = boxed_solution
        
        # Use parsed content for savepoint and response
        final_content = parsed_content
        
        # Save to savepoint if requested
        if savepoint_id and handler.savepoint_repo:
            await handler.savepoint_repo.save_savepoint(savepoint_id, final_content)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Log the timing
        model_name = model_config.name if model_config else "unknown"
        savepoint_info = f" (savepoint: {savepoint_id})" if savepoint_id else ""
        message_count = len(conversation_history)
        print(f"[MESSAGES TIMING] {message_count} messages | Model: {model_name} | Duration: {duration:.2f}s{savepoint_info}")
        
        return PromptResponse(
            content=final_content,
            savepoint_id=savepoint_id,
            was_cached=False,
            model_used=model_name,
            execution_time=duration,
            json_parsed=False,  # Chat completion doesn't support JSON parsing
            json_errors=None
        )
        
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        
        model_name = model_config.name if model_config else "unknown"
        print(f"[MESSAGES TIMING] {len(conversation_history)} messages | Model: {model_name} | Duration: {duration:.2f}s (ERROR)")
        
        raise StoryGenerationError(f"Failed to execute chat completion: {e}") from e


def load_prompt(
    handler: PromptHandler,
    prompt_id: str,
    variables: Optional[Dict[str, Any]] = None
) -> str:
    """
    Load prompt text with substitutions directly from a prompt ID and substitution list.
    
    This utility function loads a prompt template and applies variable substitutions
    without executing the prompt. Useful for getting formatted prompt text for
    custom conversation building.
    
    Args:
        handler: PromptHandler instance
        prompt_id: ID of the prompt to load
        variables: Variables to substitute in the prompt (optional)
        
    Returns:
        Formatted prompt text with substitutions applied
    """
    try:
        # Load the prompt template
        prompt_template = handler.prompt_loader.load_prompt(prompt_id)
        
        if not prompt_template:
            raise ValueError(f"Prompt template not found for ID: {prompt_id}")
        
        # Apply variable substitutions if provided
        if variables:
            try:
                # Simple string substitution for common patterns
                formatted_prompt = prompt_template
                for key, value in variables.items():
                    placeholder = f"{{{key}}}"
                    if placeholder in formatted_prompt:
                        formatted_prompt = formatted_prompt.replace(placeholder, str(value))
                
                return formatted_prompt
            except Exception as e:
                print(f"[PROMPT LOADER] Warning: Error applying variables to prompt {prompt_id}: {e}")
                return prompt_template
        else:
            return prompt_template
            
    except Exception as e:
        print(f"[PROMPT LOADER] Error loading prompt {prompt_id}: {e}")
        return f"Error loading prompt {prompt_id}: {e}"


async def execute_json_prompt_with_savepoint(
    handler: PromptHandler,
    prompt_id: str,
    required_attributes: list,
    variables: Optional[Dict[str, Any]] = None,
    savepoint_id: Optional[str] = None,
    prepend_message: Optional[str] = None,
    model_config: Optional[ModelConfig] = None,
    force_regenerate: bool = False,
    system_message: Optional[str] = None,
    skip_validation: bool = False,
    **kwargs
) -> Dict[str, Any]:
    """
    Simple wrapper function for JSON prompt execution with savepoint management.
    
    Args:
        handler: PromptHandler instance
        prompt_id: ID of the prompt to execute
        required_attributes: List of required JSON attributes
        variables: Variables to substitute in the prompt
        savepoint_id: ID for the savepoint (optional)
        prepend_message: Optional message to prepend to the prompt
        model_config: Model configuration to use
        force_regenerate: Force regeneration even if savepoint exists
        system_message: Optional system message
        **kwargs: Additional arguments passed to PromptRequest
        
    Returns:
        Dictionary containing the JSON response
    """
    request = PromptRequest(
        prompt_id=prompt_id,
        variables=variables,
        savepoint_id=savepoint_id,
        prepend_message=prepend_message,
        model_config=model_config,
        force_regenerate=force_regenerate,
        system_message=system_message,
        **kwargs
    )
    
    return await handler.execute_json_prompt(request, required_attributes)


async def execute_json_prompt(
    handler: PromptHandler,
    prompt_id: str,
    required_attributes: list,
    variables: Optional[Dict[str, Any]] = None,
    prepend_message: Optional[str] = None,
    model_config: Optional[ModelConfig] = None,
    system_message: Optional[str] = None,
    skip_validation: bool = False,
    **kwargs
) -> Dict[str, Any]:
    """
    Simple wrapper function for JSON prompt execution without savepoint management.
    
    Args:
        handler: PromptHandler instance
        prompt_id: ID of the prompt to execute
        required_attributes: List of required JSON attributes
        variables: Variables to substitute in the prompt
        prepend_message: Optional message to prepend to the prompt
        model_config: Model configuration to use
        system_message: Optional system message
        **kwargs: Additional arguments passed to PromptRequest
        
    Returns:
        Dictionary containing the JSON response
    """
    request = PromptRequest(
        prompt_id=prompt_id,
        variables=variables,
        savepoint_id=None,  # No savepoint management
        prepend_message=prepend_message,
        model_config=model_config,
        system_message=system_message,
        **kwargs
    )
    
    return await handler.execute_json_prompt(request, required_attributes)


async def execute_json_prompt_with_savepoint_lite(
    handler: PromptHandler,
    prompt_id: str,
    json_schema: Dict[str, Any],
    variables: Optional[Dict[str, Any]] = None,
    savepoint_id: Optional[str] = None,
    prepend_message: Optional[str] = None,
    model_config: Optional[ModelConfig] = None,
    force_regenerate: bool = False,
    system_message: Optional[str] = None,
    skip_validation: bool = False,
    **kwargs
) -> PromptResponse:
    """
    Execute a prompt that returns JSON with savepoint management using LiteLLMJson.
    
    Args:
        handler: PromptHandler instance
        prompt_id: ID of the prompt to execute
        json_schema: JSON schema for parsing response
        variables: Variables to substitute in the prompt
        savepoint_id: ID for the savepoint (optional)
        prepend_message: Optional message to prepend to the prompt
        model_config: Model configuration to use
        force_regenerate: Force regeneration even if savepoint exists
        system_message: Optional system message
        **kwargs: Additional arguments passed to PromptRequest
        
    Returns:
        PromptResponse with parsed JSON content and metadata
    """
    return await execute_prompt_with_savepoint(
        handler=handler,
        prompt_id=prompt_id,
        variables=variables,
        savepoint_id=savepoint_id,
        prepend_message=prepend_message,
        model_config=model_config,
        force_regenerate=force_regenerate,
        system_message=system_message,
        expect_json=True,
        json_schema=json_schema,
        skip_validation=skip_validation,
        **kwargs
    )


# Convenience function that creates a handler and executes a prompt
async def quick_prompt(
    model_provider,
    prompt_loader,
    savepoint_repo,
    prompt_id: str,
    variables: Optional[Dict[str, Any]] = None,
    savepoint_id: Optional[str] = None,
    prepend_message: Optional[str] = None,
    model_config: Optional[ModelConfig] = None,
    force_regenerate: bool = False,
    system_message: Optional[str] = None,
    skip_validation: bool = False,
    **kwargs
) -> PromptResponse:
    """
    Quick function to execute a prompt without manually creating a handler.
    
    Args:
        model_provider: Model provider instance
        prompt_loader: Prompt loader instance
        savepoint_repo: Savepoint repository instance
        prompt_id: ID of the prompt to execute
        variables: Variables to substitute in the prompt
        savepoint_id: ID for the savepoint (optional)
        prepend_message: Optional message to prepend to the prompt
        model_config: Model configuration to use
        force_regenerate: Force regeneration even if savepoint exists
        system_message: Optional system message
        **kwargs: Additional arguments passed to PromptRequest
        
    Returns:
        PromptResponse with the generated content and metadata
    """
    handler = PromptHandler(
        model_provider=model_provider,
        prompt_loader=prompt_loader,
        savepoint_repo=savepoint_repo
    )
    
    return await execute_prompt_with_savepoint(
        handler=handler,
        prompt_id=prompt_id,
        variables=variables,
        savepoint_id=savepoint_id,
        prepend_message=prepend_message,
        model_config=model_config,
        force_regenerate=force_regenerate,
        system_message=system_message,
        skip_validation=skip_validation,
        **kwargs
    ) 