"""Storage provider interface."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any


class StorageProvider(ABC):
    """Interface for storage operations."""
    
    @abstractmethod
    async def save_file(self, path: Path, content: str) -> None:
        """Save content to a file."""
        pass
    
    @abstractmethod
    async def load_file(self, path: Path) -> Optional[str]:
        """Load content from a file."""
        pass
    
    @abstractmethod
    async def file_exists(self, path: Path) -> bool:
        """Check if a file exists."""
        pass
    
    @abstractmethod
    async def delete_file(self, path: Path) -> bool:
        """Delete a file."""
        pass
    
    @abstractmethod
    async def save_json(self, path: Path, data: Dict[str, Any]) -> None:
        """Save data as JSON."""
        pass
    
    @abstractmethod
    async def load_json(self, path: Path) -> Optional[Dict[str, Any]]:
        """Load data from JSON."""
        pass
    
    @abstractmethod
    async def create_directory(self, path: Path) -> None:
        """Create a directory."""
        pass
    
    @abstractmethod
    async def directory_exists(self, path: Path) -> bool:
        """Check if a directory exists."""
        pass
    
    @abstractmethod
    async def list_files(self, path: Path, pattern: str = "*") -> list[Path]:
        """List files in a directory."""
        pass 