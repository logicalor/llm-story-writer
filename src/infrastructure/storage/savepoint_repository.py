"""Filesystem savepoint repository implementation."""

import asyncio
import json
from pathlib import Path
from typing import Optional, Any, Dict
from domain.repositories.savepoint_repository import SavepointRepository
from domain.exceptions import StorageError


class FilesystemSavepointRepository(SavepointRepository):
    """Filesystem-based savepoint repository implementation."""

    def __init__(self, base_path: Path = Path("SavePoints")):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
        self._current_story_dir: Optional[Path] = None

    def set_story_directory(self, prompt_filename: str) -> None:
        """Set the savepoint directory for the current story based on prompt filename."""
        # Remove extension and create directory name
        story_name = Path(prompt_filename).stem
        self._current_story_dir = self.base_path / story_name
        self._current_story_dir.mkdir(exist_ok=True)

    def _get_savepoint_base(self, step_name: str) -> Path:
        """Return the base path (no extension) for a savepoint."""
        if not self._current_story_dir:
            raise StorageError(
                "Story directory not set. Call set_story_directory() first."
            )

        # Handle subpath in step_name (e.g., 'some/handle' -> subfolder structure)
        if "/" in step_name or "\\" in step_name:
            # Split the step_name into path components
            path_parts = step_name.replace("\\", "/").split("/")
            # The last part is the filename, the rest are subdirectories
            filename = path_parts[-1]
            subdirs = path_parts[:-1]

            # Create the full path with subdirectories
            savepoint_path = self._current_story_dir
            for subdir in subdirs:
                savepoint_path = savepoint_path / subdir

            # Ensure the directory exists
            savepoint_path.mkdir(parents=True, exist_ok=True)

            return savepoint_path / filename
        else:
            # Simple case - just sanitize the step name
            safe_step_name = step_name.replace("/", "_").replace("\\", "_")
            return self._current_story_dir / safe_step_name

    async def save_savepoint(self, step_name: str, data: Any) -> None:
        """Save data to a savepoint."""
        try:
            base = self._get_savepoint_base(step_name)
            if isinstance(data, str):
                path = base.with_suffix(".md")
                await asyncio.to_thread(path.write_text, data, "utf-8")
            else:
                path = base.with_suffix(".json")
                content = json.dumps(data, indent=2, ensure_ascii=False)
                await asyncio.to_thread(path.write_text, content, "utf-8")
        except Exception as e:
            raise StorageError(f"Failed to save savepoint {step_name}: {e}") from e

    async def load_savepoint(self, step_name: str) -> Optional[Any]:
        """Load data from a savepoint."""
        try:
            base = self._get_savepoint_base(step_name)
            json_path = base.with_suffix(".json")
            md_path = base.with_suffix(".md")

            if await asyncio.to_thread(json_path.exists):
                content = await asyncio.to_thread(json_path.read_text, "utf-8")
                return json.loads(content)
            if await asyncio.to_thread(md_path.exists):
                return await asyncio.to_thread(md_path.read_text, "utf-8")
            return None

        except Exception as e:
            raise StorageError(f"Failed to load savepoint {step_name}: {e}") from e

    async def load_savepoint_with_metadata(
        self, step_name: str
    ) -> Optional[Dict[str, Any]]:
        """Load savepoint. Returns {"_body": data, "_frontmatter": {}} for backward compat."""
        try:
            data = await self.load_savepoint(step_name)
            if data is None:
                return None
            return {"_frontmatter": {}, "_body": data}

        except Exception as e:
            raise StorageError(
                f"Failed to load savepoint with metadata {step_name}: {e}"
            ) from e

    async def has_savepoint(self, step_name: str) -> bool:
        """Check if a savepoint exists."""
        try:
            base = self._get_savepoint_base(step_name)
            json_exists = await asyncio.to_thread(base.with_suffix(".json").exists)
            if json_exists:
                return True
            return await asyncio.to_thread(base.with_suffix(".md").exists)
        except Exception as e:
            raise StorageError(
                f"Failed to check savepoint existence {step_name}: {e}"
            ) from e

    async def delete_savepoint(self, step_name: str) -> bool:
        """Delete a savepoint."""
        try:
            base = self._get_savepoint_base(step_name)
            deleted = False
            for path in [base.with_suffix(".json"), base.with_suffix(".md")]:
                if await asyncio.to_thread(path.exists):
                    await asyncio.to_thread(path.unlink)
                    deleted = True
            return deleted
        except Exception as e:
            raise StorageError(f"Failed to delete savepoint {step_name}: {e}") from e

    async def list_savepoint_names(self) -> list[str]:
        """List savepoint step names only (no data loaded).

        Much faster than list_savepoints() — just scans filenames
        without reading/parsing file contents.
        """
        try:
            if not self._current_story_dir:
                return []

            seen: set[str] = set()
            for pattern in ("*.md", "*.json"):
                for file_path in await asyncio.to_thread(
                    self._current_story_dir.rglob, pattern
                ):
                    relative_path = file_path.relative_to(self._current_story_dir)
                    step_name = str(relative_path.with_suffix("")).replace("\\", "/")
                    seen.add(step_name)

            return sorted(seen)
        except Exception as e:
            raise StorageError(f"Failed to list savepoint names: {e}") from e

    async def list_savepoints(self) -> Dict[str, Any]:
        """List all available savepoints for the current story."""
        try:
            if not self._current_story_dir:
                return {}

            savepoints: dict[str, Any] = {}
            for step_name in await self.list_savepoint_names():
                try:
                    savepoints[step_name] = await self.load_savepoint(step_name)
                except Exception:
                    continue

            return savepoints
        except Exception as e:
            raise StorageError(f"Failed to list savepoints: {e}") from e

    async def clear_all_savepoints(self) -> None:
        """Clear all savepoints for the current story."""
        try:
            if not self._current_story_dir:
                return

            for pattern in ("*.md", "*.json"):
                for file_path in await asyncio.to_thread(
                    self._current_story_dir.rglob, pattern
                ):
                    await asyncio.to_thread(file_path.unlink)

            # Remove empty directories
            for dir_path in reversed(
                list(await asyncio.to_thread(self._current_story_dir.rglob, "*"))
            ):
                if dir_path.is_dir() and dir_path != self._current_story_dir:
                    try:
                        await asyncio.to_thread(dir_path.rmdir)
                    except OSError:
                        # Directory not empty, skip
                        pass
        except Exception as e:
            raise StorageError(f"Failed to clear savepoints: {e}") from e
