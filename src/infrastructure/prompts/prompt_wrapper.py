"""Simple wrapper functions for prompt execution with savepoint management."""

from typing import Dict, Any, Optional
from domain.value_objects.model_config import ModelConfig
from .prompt_handler import PromptHandler, PromptRequest, PromptResponse


async def execute_prompt_with_savepoint(
    handler: PromptHandler,
    prompt_id: str,
    variables: Optional[Dict[str, Any]] = None,
    savepoint_id: Optional[str] = None,
    prepend_message: Optional[str] = None,
    model_config: Optional[ModelConfig] = None,
    force_regenerate: bool = False,
    system_message: Optional[str] = None,
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
        **kwargs
    )
    
    response = await handler.execute_prompt(request)
    
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
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Log the timing
    model_name = model_config.name if model_config else "unknown"
    print(f"[PROMPT TIMING] {prompt_id} | Model: {model_name} | Duration: {duration:.2f}s")
    
    return response


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
        **kwargs
    ) 