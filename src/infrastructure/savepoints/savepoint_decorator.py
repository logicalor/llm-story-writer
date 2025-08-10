"""Savepoint decorator for automatic model response saving."""

import functools
import inspect
from typing import Any, Callable, Optional
from domain.repositories.savepoint_repository import SavepointRepository


def with_savepoint(
    step_name: str,
    savepoint_repo: SavepointRepository,
    save_args: bool = False,
    save_kwargs: bool = False
):
    """
    Decorator to automatically save model responses to savepoints.
    
    Args:
        step_name: Name of the savepoint step
        savepoint_repo: Savepoint repository instance
        save_args: Whether to save function arguments as well
        save_kwargs: Whether to save function keyword arguments as well
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Check if we have a savepoint for this step
            if await savepoint_repo.has_savepoint(step_name):
                # Load and return the saved result
                saved_data = await savepoint_repo.load_savepoint(step_name)
                if saved_data is not None:
                    return saved_data
            
            # Execute the function
            result = await func(*args, **kwargs)
            
            # Save the result directly (scalar values only)
            await savepoint_repo.save_savepoint(step_name, result)
            
            return result
        
        return wrapper
    return decorator


def savepoint_step(
    step_name: str,
    savepoint_repo: SavepointRepository
):
    """
    Simple decorator that just saves the result of a model call.
    This is the most common use case for the outline-chapter strategy.
    """
    return with_savepoint(step_name, savepoint_repo, save_args=False, save_kwargs=False)


class SavepointManager:
    """Helper class to manage savepoints for a story generation session."""
    
    def __init__(self, savepoint_repo: SavepointRepository, prompt_filename: str):
        self.savepoint_repo = savepoint_repo
        self.prompt_filename = prompt_filename
        self.savepoint_repo.set_story_directory(prompt_filename)
    
    def step(self, step_name: str):
        """Create a savepoint decorator for a specific step."""
        return savepoint_step(step_name, self.savepoint_repo)
    
    async def has_step(self, step_name: str) -> bool:
        """Check if a step has been completed."""
        return await self.savepoint_repo.has_savepoint(step_name)
    
    async def load_step(self, step_name: str) -> Optional[Any]:
        """Load a completed step."""
        return await self.savepoint_repo.load_savepoint(step_name)
    
    async def save_step(self, step_name: str, result: Any) -> None:
        """Manually save a step result."""
        await self.savepoint_repo.save_savepoint(step_name, result)
    
    async def clear_story_savepoints(self) -> None:
        """Clear all savepoints for the current story."""
        await self.savepoint_repo.clear_all_savepoints()
    
    async def list_story_savepoints(self) -> dict:
        """List all savepoints for the current story."""
        return await self.savepoint_repo.list_savepoints() 