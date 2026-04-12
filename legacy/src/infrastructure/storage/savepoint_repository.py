"""Filesystem savepoint repository implementation."""

import asyncio
import yaml
import re
from pathlib import Path
from typing import Optional, Any, Dict, Union
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
    
    def _get_savepoint_path(self, step_name: str) -> Path:
        """Get the full path for a savepoint."""
        if not self._current_story_dir:
            raise StorageError("Story directory not set. Call set_story_directory() first.")
        
        # Handle subpath in step_name (e.g., 'some/handle' -> subfolder structure)
        if '/' in step_name or '\\' in step_name:
            # Split the step_name into path components
            path_parts = step_name.replace('\\', '/').split('/')
            # The last part is the filename, the rest are subdirectories
            filename = path_parts[-1]
            subdirs = path_parts[:-1]
            
            # Create the full path with subdirectories
            savepoint_path = self._current_story_dir
            for subdir in subdirs:
                savepoint_path = savepoint_path / subdir
            
            # Ensure the directory exists
            savepoint_path.mkdir(parents=True, exist_ok=True)
            
            # Return the full path with .md extension
            return savepoint_path / f"{filename}.md"
        else:
            # Simple case - just sanitize the step name
            safe_step_name = step_name.replace("/", "_").replace("\\", "_")
            return self._current_story_dir / f"{safe_step_name}.md"
    
    def _is_scalar(self, data: Any) -> bool:
        """Check if data is a scalar value that can be stored as markdown."""
        return isinstance(data, (str, int, float, bool)) or data is None
    
    def _is_supported_type(self, data: Any) -> bool:
        """Check if data is a supported type for savepoint storage."""
        if self._is_scalar(data):
            return True
        if isinstance(data, (dict, list)):
            return True
        return False
    
    def _extract_content_from_markdown(self, content: str) -> Any:
        """Extract the original value from markdown content."""
        lines = content.split('\n')
        
        # Skip the header line
        if len(lines) < 2:
            return None
        
        # Extract the value based on the type information
        if "**Type:** Boolean" in content:
            # Extract boolean value
            for line in lines:
                if line.startswith("**Value:**"):
                    value_str = line.split("**Value:**")[1].strip()
                    return value_str.lower() == "true"
        elif "**Type:** int" in content:
            # Extract integer value
            for line in lines:
                if line.startswith("**Value:**"):
                    value_str = line.split("**Value:**")[1].strip()
                    return int(value_str)
        elif "**Type:** float" in content:
            # Extract float value
            for line in lines:
                if line.startswith("**Value:**"):
                    value_str = line.split("**Value:**")[1].strip()
                    return float(value_str)
        elif "This savepoint contains no data." in content:
            # Return None
            return None
        else:
            # Extract string value (everything after the header)
            # Remove the first line (header) and join the rest
            return '\n'.join(lines[1:]).strip()
    
    async def save_savepoint(self, step_name: str, data: Any) -> None:
        """Save data to a savepoint."""
        try:
            # Check if data type is supported
            if not self._is_supported_type(data):
                raise StorageError(
                    f"Cannot save data of type {type(data).__name__}. "
                    f"Only str, int, float, bool, dict, list, and None are supported."
                )
            
            savepoint_path = self._get_savepoint_path(step_name)
            
            # Handle different data types
            if data is None:
                content = "# Savepoint: None\n\nThis savepoint contains no data."
            elif self._is_scalar(data):
                # Handle scalar values as before
                if isinstance(data, bool):
                    content = f"# Savepoint: {step_name}\n\n**Value:** {data}\n\n**Type:** Boolean"
                elif isinstance(data, (int, float)):
                    content = f"# Savepoint: {step_name}\n\n**Value:** {data}\n\n**Type:** {type(data).__name__}"
                else:  # str
                    content = f"# Savepoint: {step_name}\n\n{data}"
            else:
                # Handle complex data types (dict, list) with YAML frontmatter
                if isinstance(data, dict) and "_frontmatter" in data and "_body" in data:
                    # Handle our new savepoint data structure
                    frontmatter = data["_frontmatter"]
                    body = data["_body"]
                    
                    # Convert frontmatter to YAML
                    yaml_frontmatter = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)
                    
                    # Format the body content
                    if isinstance(body, str):
                        body_content = body
                    else:
                        body_content = yaml.dump(body, default_flow_style=False, allow_unicode=True)
                    
                    content = f"---\n{yaml_frontmatter}---\n\n# Savepoint: {step_name}\n\n{body_content}"
                else:
                    # Handle regular complex data types
                    yaml_data = yaml.dump(data, default_flow_style=False, allow_unicode=True)
                    content = f"---\n{yaml_data}---\n\n# Savepoint: {step_name}\n\nData saved in YAML frontmatter above."
            
            # Save as markdown
            await asyncio.to_thread(
                savepoint_path.write_text,
                content,
                encoding='utf-8'
            )
        except Exception as e:
            raise StorageError(f"Failed to save savepoint {step_name}: {e}") from e
    
    async def load_savepoint(self, step_name: str) -> Optional[Any]:
        """Load data from a savepoint."""
        try:
            savepoint_path = self._get_savepoint_path(step_name)
            
            if not await asyncio.to_thread(savepoint_path.exists):
                return None
            
            # Load markdown content
            content = await asyncio.to_thread(
                savepoint_path.read_text,
                encoding='utf-8'
            )
            
            # Check if content has YAML frontmatter
            if content.startswith('---'):
                # Extract YAML frontmatter
                frontmatter_match = re.search(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
                if frontmatter_match:
                    yaml_content = frontmatter_match.group(1)
                    try:
                        frontmatter_data = yaml.safe_load(yaml_content)
                        
                        # Check if this is our new savepoint structure with _frontmatter and _body
                        if isinstance(frontmatter_data, dict) and "_frontmatter" in frontmatter_data and "_body" in frontmatter_data:
                            # Return only the body content for backward compatibility
                            return frontmatter_data["_body"]
                        else:
                            # Handle legacy format - extract content from markdown body
                            # Remove the frontmatter and extract the actual content
                            body_content = content[frontmatter_match.end():].strip()
                            # Parse the markdown to extract the original value
                            return self._extract_content_from_markdown(body_content)
                    except yaml.YAMLError as e:
                        raise StorageError(f"Failed to parse YAML frontmatter in savepoint {step_name}: {e}") from e
            
            # Parse the markdown to extract the original value (legacy format)
            return self._extract_content_from_markdown(content)
                
        except Exception as e:
            raise StorageError(f"Failed to load savepoint {step_name}: {e}") from e
    
    async def load_savepoint_with_metadata(self, step_name: str) -> Optional[Dict[str, Any]]:
        """Load savepoint with full metadata including frontmatter and body."""
        try:
            savepoint_path = self._get_savepoint_path(step_name)
            
            if not await asyncio.to_thread(savepoint_path.exists):
                return None
            
            # Load markdown content
            content = await asyncio.to_thread(
                savepoint_path.read_text,
                encoding='utf-8'
            )
            
            # Check if content has YAML frontmatter
            if content.startswith('---'):
                # Extract YAML frontmatter
                frontmatter_match = re.search(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
                if frontmatter_match:
                    yaml_content = frontmatter_match.group(1)
                    try:
                        frontmatter_data = yaml.safe_load(yaml_content)
                        
                        # Check if this is our new savepoint structure with _frontmatter and _body
                        if isinstance(frontmatter_data, dict) and "_frontmatter" in frontmatter_data and "_body" in frontmatter_data:
                            # Return the full structure
                            return frontmatter_data
                        else:
                            # This is our new savepoint structure where frontmatter contains metadata
                            # and the body content is in the markdown after the frontmatter
                            body_content = content[frontmatter_match.end():].strip()
                            # Extract the actual content from the markdown body
                            actual_body = self._extract_content_from_markdown(body_content)
                            
                            return {
                                "_frontmatter": frontmatter_data,
                                "_body": actual_body
                            }
                    except yaml.YAMLError as e:
                        raise StorageError(f"Failed to parse YAML frontmatter in savepoint {step_name}: {e}") from e
            
            # For legacy format without frontmatter, wrap the content
            body_content = await self.load_savepoint(step_name)
            return {
                "_frontmatter": {"legacy_data": True},
                "_body": body_content
            }
                
        except Exception as e:
            raise StorageError(f"Failed to load savepoint with metadata {step_name}: {e}") from e
    
    async def has_savepoint(self, step_name: str) -> bool:
        """Check if a savepoint exists."""
        try:
            savepoint_path = self._get_savepoint_path(step_name)
            return await asyncio.to_thread(savepoint_path.exists)
        except Exception as e:
            raise StorageError(f"Failed to check savepoint existence {step_name}: {e}") from e
    
    async def delete_savepoint(self, step_name: str) -> bool:
        """Delete a savepoint."""
        try:
            savepoint_path = self._get_savepoint_path(step_name)
            
            if not await asyncio.to_thread(savepoint_path.exists):
                return False
            
            await asyncio.to_thread(savepoint_path.unlink)
            return True
        except Exception as e:
            raise StorageError(f"Failed to delete savepoint {step_name}: {e}") from e
    
    async def list_savepoints(self) -> Dict[str, Any]:
        """List all available savepoints for the current story."""
        try:
            if not self._current_story_dir:
                return {}
            
            savepoints = {}
            
            # Recursively find all .md files
            for file_path in await asyncio.to_thread(
                self._current_story_dir.rglob, "*.md"
            ):
                # Calculate the relative path from the story directory
                relative_path = file_path.relative_to(self._current_story_dir)
                
                # Convert the file path back to the step name
                # Remove .md extension and convert path separators
                step_name = str(relative_path.with_suffix('')).replace('\\', '/')
                
                try:
                    data = await self.load_savepoint(step_name)
                    savepoints[step_name] = data
                except Exception:
                    # Skip corrupted savepoints
                    continue
            
            return savepoints
        except Exception as e:
            raise StorageError(f"Failed to list savepoints: {e}") from e
    
    async def clear_all_savepoints(self) -> None:
        """Clear all savepoints for the current story."""
        try:
            if not self._current_story_dir:
                return
            
            # Recursively remove all .md files
            for file_path in await asyncio.to_thread(
                self._current_story_dir.rglob, "*.md"
            ):
                await asyncio.to_thread(file_path.unlink)
            
            # Remove empty directories
            for dir_path in reversed(list(await asyncio.to_thread(
                self._current_story_dir.rglob, "*"
            ))):
                if dir_path.is_dir() and dir_path != self._current_story_dir:
                    try:
                        await asyncio.to_thread(dir_path.rmdir)
                    except OSError:
                        # Directory not empty, skip
                        pass
        except Exception as e:
            raise StorageError(f"Failed to clear savepoints: {e}") from e 