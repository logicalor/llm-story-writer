"""Story repository interface."""

from abc import ABC, abstractmethod
from typing import Optional, List
from ..entities.story import Story


class StoryRepository(ABC):
    """Interface for story data access."""
    
    @abstractmethod
    async def save(self, story: Story) -> str:
        """Save a story and return its ID."""
        pass
    
    @abstractmethod
    async def get_by_id(self, story_id: str) -> Optional[Story]:
        """Get a story by its ID."""
        pass
    
    @abstractmethod
    async def get_by_title(self, title: str) -> Optional[Story]:
        """Get a story by its title."""
        pass
    
    @abstractmethod
    async def list_all(self) -> List[Story]:
        """Get all stories."""
        pass
    
    @abstractmethod
    async def delete(self, story_id: str) -> bool:
        """Delete a story by its ID."""
        pass
    
    @abstractmethod
    async def exists(self, story_id: str) -> bool:
        """Check if a story exists."""
        pass 