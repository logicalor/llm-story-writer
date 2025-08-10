"""File storage implementation."""

import asyncio
import json
from pathlib import Path
from typing import Any, Optional, Dict
from application.interfaces.storage_provider import StorageProvider
from domain.exceptions import StorageError


class FileStorage(StorageProvider):
    """File-based storage implementation."""
    
    def __init__(self, base_path: Path = Path(".")):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
    
    async def save_file(self, path: Path, content: str) -> None:
        """Save content to a file."""
        try:
            full_path = self.base_path / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            await asyncio.to_thread(
                full_path.write_text,
                content,
                encoding='utf-8'
            )
        except Exception as e:
            raise StorageError(f"Failed to save file {path}: {e}") from e
    
    async def load_file(self, path: Path) -> Optional[str]:
        """Load content from a file."""
        try:
            full_path = self.base_path / path
            
            if not await self.file_exists(path):
                return None
            
            content = await asyncio.to_thread(
                full_path.read_text,
                encoding='utf-8'
            )
            
            return content
        except Exception as e:
            raise StorageError(f"Failed to load file {path}: {e}") from e
    
    async def file_exists(self, path: Path) -> bool:
        """Check if a file exists."""
        try:
            full_path = self.base_path / path
            return await asyncio.to_thread(full_path.exists)
        except Exception as e:
            raise StorageError(f"Failed to check file existence {path}: {e}") from e
    
    async def delete_file(self, path: Path) -> bool:
        """Delete a file."""
        try:
            full_path = self.base_path / path
            
            if not await self.file_exists(path):
                return False
            
            await asyncio.to_thread(full_path.unlink)
            return True
        except Exception as e:
            raise StorageError(f"Failed to delete file {path}: {e}") from e
    
    async def save_json(self, path: Path, data: Dict[str, Any]) -> None:
        """Save data as JSON."""
        try:
            full_path = self.base_path / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            await asyncio.to_thread(
                full_path.write_text,
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
        except Exception as e:
            raise StorageError(f"Failed to save JSON file {path}: {e}") from e
    
    async def load_json(self, path: Path) -> Optional[Dict[str, Any]]:
        """Load data from JSON."""
        try:
            content = await self.load_file(path)
            if content is None:
                return None
            
            return await asyncio.to_thread(json.loads, content)
        except Exception as e:
            raise StorageError(f"Failed to load JSON file {path}: {e}") from e
    
    async def create_directory(self, path: Path) -> None:
        """Create a directory."""
        try:
            full_path = self.base_path / path
            await asyncio.to_thread(full_path.mkdir, parents=True, exist_ok=True)
        except Exception as e:
            raise StorageError(f"Failed to create directory {path}: {e}") from e
    
    async def directory_exists(self, path: Path) -> bool:
        """Check if a directory exists."""
        try:
            full_path = self.base_path / path
            return await asyncio.to_thread(full_path.is_dir)
        except Exception as e:
            raise StorageError(f"Failed to check directory existence {path}: {e}") from e
    
    async def list_files(self, path: Path, pattern: str = "*") -> list[Path]:
        """List files in a directory."""
        try:
            full_path = self.base_path / path
            
            if not await self.directory_exists(path):
                return []
            
            files = await asyncio.to_thread(
                list,
                full_path.glob(pattern)
            )
            
            # Convert to relative paths
            return [file.relative_to(self.base_path) for file in files]
        except Exception as e:
            raise StorageError(f"Failed to list files in {path}: {e}") from e 