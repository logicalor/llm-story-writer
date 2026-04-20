"""Savepoint repository interface."""

from abc import ABC, abstractmethod
from typing import Optional, Any, Dict


class SavepointRepository(ABC):
    """Interface for savepoint data access."""

    @abstractmethod
    def set_story_directory(self, prompt_filename: str) -> None:
        """Set the savepoint directory for the current story."""
        pass

    @abstractmethod
    async def save_savepoint(self, step_name: str, data: Any) -> None:
        """Save data to a savepoint."""
        pass

    @abstractmethod
    async def load_savepoint(self, step_name: str) -> Optional[Any]:
        """Load data from a savepoint."""
        pass

    @abstractmethod
    async def load_savepoint_with_metadata(
        self, step_name: str
    ) -> Optional[Dict[str, Any]]:
        """Load savepoint with full metadata including frontmatter and body."""
        pass

    @abstractmethod
    async def has_savepoint(self, step_name: str) -> bool:
        """Check if a savepoint exists."""
        pass

    @abstractmethod
    async def delete_savepoint(self, step_name: str) -> bool:
        """Delete a savepoint."""
        pass

    @abstractmethod
    async def list_savepoints(self) -> Dict[str, Any]:
        """List all available savepoints."""
        pass

    @abstractmethod
    async def list_savepoint_names(self) -> list[str]:
        """List all savepoint step names (no data loaded)."""
        pass

    @abstractmethod
    async def clear_all_savepoints(self) -> None:
        """Clear all savepoints."""
        pass
