"""RAG integration service for story generation pipeline.

This service now uses the rag-query tool via subprocess instead of RAGService.
"""

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

from application.services.content_chunker import ContentChunker

logger = logging.getLogger(__name__)


class RAGIntegrationService:
    """Service for integrating RAG capabilities with the story generation pipeline.

    Uses the rag-query tool via subprocess for all ChromaDB operations.
    """

    def __init__(self, content_chunker: ContentChunker):
        self.content_chunker = content_chunker
        self._current_story_identifier: Optional[str] = None

    def _run_rag_query(self, operation: str, name: str, **kwargs) -> Dict[str, Any]:
        """Run the rag_query.py tool via subprocess.

        Args:
            operation: 'index' or 'query'
            name: Story name
            **kwargs: Additional arguments for the operation

        Returns:
            Parsed JSON response from the tool
        """
        cmd = [
            sys.executable,
            "-m",
            "src.tools.rag_query",
            "--operation",
            operation,
            "--name",
            name,
        ]

        # Add optional arguments
        for key, value in kwargs.items():
            if value is not None:
                arg_name = f"--{key.replace('_', '-')}"
                cmd.extend([arg_name, str(value)])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            logger.error(f"rag_query failed: {e.stderr}")
            raise RuntimeError(f"rag_query tool failed: {e.stderr}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse rag_query output: {e}")
            raise RuntimeError(f"Invalid JSON from rag_query: {e}")

    def set_current_story_identifier(self, story_identifier: str) -> None:
        """Set the current story identifier for RAG operations."""
        self._current_story_identifier = story_identifier
        logger.info(f"Set current story identifier: {story_identifier}")

    def get_current_story_identifier(self) -> Optional[str]:
        """Get the current story identifier."""
        return self._current_story_identifier

    async def initialize_story(
        self, story_identifier: str, story_name: Optional[str] = None
    ) -> str:
        """Initialize a story in the RAG system using a story identifier.

        For ChromaDB, stories are created on-demand when content is indexed.
        This method validates the story name and returns it.
        """
        if not story_name:
            story_name = Path(story_identifier).stem

        # Validate story name (basic validation)
        if not story_name or "/" in story_name or "\\" in story_name:
            raise ValueError(f"Invalid story name: {story_name}")

        logger.info(f"Initialized story '{story_name}'")
        return story_name

    def _get_story_name(self, story_identifier: Optional[str] = None) -> str:
        """Get story name from identifier or current story."""
        identifier = story_identifier or self._current_story_identifier
        if not identifier:
            raise ValueError("No story identifier available for RAG operations")
        return Path(identifier).stem

    async def cleanup_content_by_type_and_metadata(
        self,
        content_type: str,
        metadata_filters: Optional[Dict[str, Any]] = None,
        story_identifier: Optional[str] = None,
    ) -> int:
        """Clean up content chunks by type and metadata before re-indexing.

        Note: ChromaDB doesn't support partial deletion via the CLI tool.
        This is a no-op for now - content is overwritten on re-index.
        """
        logger.warning(
            "cleanup_content_by_type_and_metadata is not implemented for ChromaDB. "
            "Content is overwritten on re-index."
        )
        return 0

    async def index_outline(
        self,
        outline_content: str,
        chapter_number: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        story_identifier: Optional[str] = None,
    ) -> List[str]:
        """Index story outline content."""
        story_name = self._get_story_name(story_identifier)

        # Chunk the outline content
        chunks = self.content_chunker.chunk_text(
            outline_content,
            "outline",
            "story_outline",
            f"Outline - Chapter {chapter_number}"
            if chapter_number
            else "Story Outline",
            metadata or {},
            chapter_number,
        )

        # Index each chunk
        chunk_ids = []
        for i, chunk in enumerate(chunks):
            doc_id = f"outline-{chapter_number or 'main'}-{i}"
            self._run_rag_query(
                operation="index",
                name=story_name,
                doc_id=doc_id,
                content=chunk.content,
                content_type="outline",
                chapter_num=chunk.chapter_number,
            )
            chunk_ids.append(doc_id)

        logger.info(f"Indexed {len(chunks)} outline chunks for story '{story_name}'")
        return chunk_ids

    async def index_chapter(
        self,
        chapter_content: str,
        chapter_number: int,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        story_identifier: Optional[str] = None,
    ) -> List[str]:
        """Index chapter content."""
        story_name = self._get_story_name(story_identifier)

        # Chunk the chapter content
        chunks = self.content_chunker.chunk_chapter(
            chapter_content, chapter_number, title, metadata or {}
        )

        # Index each chunk
        chunk_ids = []
        for i, chunk in enumerate(chunks):
            doc_id = f"chapter-{chapter_number}-{i}"
            self._run_rag_query(
                operation="index",
                name=story_name,
                doc_id=doc_id,
                content=chunk.content,
                content_type="chapter",
                chapter_num=chunk.chapter_number,
            )
            chunk_ids.append(doc_id)

        logger.info(
            f"Indexed {len(chunks)} chapter chunks for story '{story_name}', "
            f"chapter {chapter_number}"
        )
        return chunk_ids

    async def index_character(
        self,
        character_content: str,
        character_name: str,
        metadata: Optional[Dict[str, Any]] = None,
        story_identifier: Optional[str] = None,
    ) -> List[str]:
        """Index character information."""
        story_name = self._get_story_name(story_identifier)

        # Chunk the character content
        chunks = self.content_chunker.chunk_character_sheet(
            character_content, character_name, metadata or {}
        )

        # Index each chunk
        chunk_ids = []
        for i, chunk in enumerate(chunks):
            doc_id = f"character-{character_name.lower().replace(' ', '-')}-{i}"
            self._run_rag_query(
                operation="index",
                name=story_name,
                doc_id=doc_id,
                content=chunk.content,
                content_type="character",
            )
            chunk_ids.append(doc_id)

        logger.info(
            f"Indexed {len(chunks)} character chunks for '{character_name}' "
            f"in story '{story_name}'"
        )
        return chunk_ids

    async def index_setting(
        self,
        setting_content: str,
        location_name: str,
        metadata: Optional[Dict[str, Any]] = None,
        story_identifier: Optional[str] = None,
    ) -> List[str]:
        """Index setting information."""
        story_name = self._get_story_name(story_identifier)

        # Chunk the setting content
        chunks = self.content_chunker.chunk_setting_description(
            setting_content, location_name, metadata or {}
        )

        # Index each chunk
        chunk_ids = []
        for i, chunk in enumerate(chunks):
            doc_id = f"setting-{location_name.lower().replace(' ', '-')}-{i}"
            self._run_rag_query(
                operation="index",
                name=story_name,
                doc_id=doc_id,
                content=chunk.content,
                content_type="setting",
            )
            chunk_ids.append(doc_id)

        logger.info(
            f"Indexed {len(chunks)} setting chunks for '{location_name}' "
            f"in story '{story_name}'"
        )
        return chunk_ids

    async def index_event(
        self,
        event_content: str,
        event_type: str,
        chapter_number: Optional[int] = None,
        scene_number: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        story_identifier: Optional[str] = None,
    ) -> str:
        """Index an event or recap."""
        story_name = self._get_story_name(story_identifier)

        doc_id = (
            f"event-{event_type.lower().replace(' ', '-')}-{chapter_number or 'global'}"
        )
        self._run_rag_query(
            operation="index",
            name=story_name,
            doc_id=doc_id,
            content=event_content,
            content_type="recap",
            chapter_num=chapter_number,
        )

        logger.info(f"Indexed event '{event_type}' for story '{story_name}'")
        return doc_id

    async def _get_character_context(self, story_name: str, chapter_number: int) -> str:
        """Get character context for a specific chapter."""
        try:
            result = self._run_rag_query(
                operation="query",
                name=story_name,
                query=f"character information chapter {chapter_number}",
                content_type="character",
                n_results=10,
            )

            results = result.get("results", [])
            if not results:
                return ""

            context_parts = []
            for item in results:
                excerpt = item.get("excerpt", "")
                if excerpt:
                    context_parts.append(excerpt)

            return "\n\n".join(context_parts)

        except Exception as e:
            logger.error(f"Failed to get character context: {e}")
            return ""

    async def _get_setting_context(self, story_name: str, chapter_number: int) -> str:
        """Get setting context for a specific chapter."""
        try:
            result = self._run_rag_query(
                operation="query",
                name=story_name,
                query=f"setting location chapter {chapter_number}",
                content_type="setting",
                n_results=10,
            )

            results = result.get("results", [])
            if not results:
                return ""

            context_parts = []
            for item in results:
                excerpt = item.get("excerpt", "")
                if excerpt:
                    context_parts.append(excerpt)

            return "\n\n".join(context_parts)

        except Exception as e:
            logger.error(f"Failed to get setting context: {e}")
            return ""

    async def _get_plot_context(self, story_name: str, chapter_number: int) -> str:
        """Get plot context from previous chapters."""
        try:
            result = self._run_rag_query(
                operation="query",
                name=story_name,
                query=f"plot outline chapter {chapter_number}",
                content_type="outline",
                n_results=5,
            )

            results = result.get("results", [])
            if not results:
                return ""

            context_parts = []
            for item in results:
                excerpt = item.get("excerpt", "")
                if excerpt:
                    context_parts.append(excerpt)

            return "\n\n".join(context_parts)

        except Exception as e:
            logger.error(f"Failed to get plot context: {e}")
            return ""

    async def _get_event_context(self, story_name: str, chapter_number: int) -> str:
        """Get recent event context."""
        try:
            result = self._run_rag_query(
                operation="query",
                name=story_name,
                query=f"events recap chapter {chapter_number}",
                content_type="recap",
                n_results=5,
            )

            results = result.get("results", [])
            if not results:
                return ""

            context_parts = []
            for item in results:
                excerpt = item.get("excerpt", "")
                if excerpt:
                    context_parts.append(excerpt)

            return "\n\n".join(context_parts)

        except Exception as e:
            logger.error(f"Failed to get event context: {e}")
            return ""

    async def get_generation_context(
        self,
        chapter_number: int,
        scene_number: Optional[int] = None,
        content_types: Optional[List[str]] = None,
        story_identifier: Optional[str] = None,
    ) -> str:
        """Get relevant context for story generation."""
        story_name = self._get_story_name(story_identifier)

        try:
            context_parts = []

            # Get character information
            if not content_types or "character" in content_types:
                character_context = await self._get_character_context(
                    story_name, chapter_number
                )
                if character_context:
                    context_parts.append("CHARACTER CONTEXT:\n" + character_context)

            # Get setting information
            if not content_types or "setting" in content_types:
                setting_context = await self._get_setting_context(
                    story_name, chapter_number
                )
                if setting_context:
                    context_parts.append("SETTING CONTEXT:\n" + setting_context)

            # Get plot context from previous chapters
            if (
                not content_types
                or "outline" in content_types
                or "scene" in content_types
            ):
                plot_context = await self._get_plot_context(story_name, chapter_number)
                if plot_context:
                    context_parts.append("PLOT CONTEXT:\n" + plot_context)

            # Get recent events
            if not content_types or "event" in content_types:
                event_context = await self._get_event_context(
                    story_name, chapter_number
                )
                if event_context:
                    context_parts.append("RECENT EVENTS:\n" + event_context)

            return "\n\n".join(context_parts)

        except Exception as e:
            logger.error(f"Failed to get context for generation: {e}")
            return ""

    async def search_story_content(
        self,
        query: str,
        content_type: Optional[str] = None,
        limit: Optional[int] = None,
        story_identifier: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search for content in a story."""
        story_name = self._get_story_name(story_identifier)

        result = self._run_rag_query(
            operation="query",
            name=story_name,
            query=query,
            content_type=content_type,
            n_results=limit or 10,
        )

        results = result.get("results", [])
        logger.debug(f"Found {len(results)} results for query in story '{story_name}'")
        return results

    async def get_story_summary(
        self, story_identifier: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get a summary of the story's indexed content."""
        story_name = self._get_story_name(story_identifier)

        content_types = ["outline", "chapter", "character", "setting", "recap"]
        content_counts: Dict[str, int] = {}

        for content_type in content_types:
            try:
                result = self._run_rag_query(
                    operation="query",
                    name=story_name,
                    query=content_type,
                    content_type=content_type,
                    n_results=100,
                )
                content_counts[content_type] = len(result.get("results", []))
            except Exception:
                content_counts[content_type] = 0

        summary = {
            "story_name": story_name,
            "content_counts": content_counts,
            "total_chunks": sum(content_counts.values()),
        }

        logger.info(f"Retrieved summary for story '{story_name}'")
        return summary

    # Legacy methods for backward compatibility
    async def index_outline_with_path(
        self,
        prompt_file_path: Path,
        outline_content: str,
        chapter_number: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Legacy method: Index story outline content with prompt file path."""
        logger.warning(
            "index_outline_with_path is deprecated. Use index_outline instead."
        )
        return await self.index_outline(
            outline_content, chapter_number, metadata, str(prompt_file_path)
        )

    async def index_chapter_with_path(
        self,
        prompt_file_path: Path,
        chapter_content: str,
        chapter_number: int,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Legacy method: Index chapter content with prompt file path."""
        logger.warning(
            "index_chapter_with_path is deprecated. Use index_chapter instead."
        )
        return await self.index_chapter(
            chapter_content, chapter_number, title, metadata, str(prompt_file_path)
        )

    async def index_character_with_path(
        self,
        prompt_file_path: Path,
        character_content: str,
        character_name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Legacy method: Index character information with prompt file path."""
        logger.warning(
            "index_character_with_path is deprecated. Use index_character instead."
        )
        return await self.index_character(
            character_content, character_name, metadata, str(prompt_file_path)
        )

    async def index_setting_with_path(
        self,
        prompt_file_path: Path,
        setting_content: str,
        location_name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Legacy method: Index setting information with prompt file path."""
        logger.warning(
            "index_setting_with_path is deprecated. Use index_setting instead."
        )
        return await self.index_setting(
            setting_content, location_name, metadata, str(prompt_file_path)
        )

    async def index_event_with_path(
        self,
        prompt_file_path: Path,
        event_content: str,
        event_type: str,
        chapter_number: Optional[int] = None,
        scene_number: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Legacy method: Index an event or recap with prompt file path."""
        logger.warning("index_event_with_path is deprecated. Use index_event instead.")
        return await self.index_event(
            event_content,
            event_type,
            chapter_number,
            scene_number,
            metadata,
            str(prompt_file_path),
        )

    async def get_generation_context_with_path(
        self,
        prompt_file_path: Path,
        chapter_number: int,
        scene_number: Optional[int] = None,
        content_types: Optional[List[str]] = None,
    ) -> str:
        """Legacy method: Get relevant context for story generation with prompt file path."""
        logger.warning(
            "get_generation_context_with_path is deprecated. Use get_generation_context instead."
        )
        return await self.get_generation_context(
            chapter_number, scene_number, content_types, str(prompt_file_path)
        )

    async def search_story_content_with_path(
        self,
        prompt_file_path: Path,
        query: str,
        content_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Legacy method: Search for content in a story with prompt file path."""
        logger.warning(
            "search_story_content_with_path is deprecated. Use search_story_content instead."
        )
        return await self.search_story_content(
            query, content_type, limit, str(prompt_file_path)
        )

    async def get_story_summary_with_path(
        self, prompt_file_path: Path
    ) -> Dict[str, Any]:
        """Legacy method: Get a summary of the story's indexed content with prompt file path."""
        logger.warning(
            "get_story_summary_with_path is deprecated. Use get_story_summary instead."
        )
        return await self.get_story_summary(str(prompt_file_path))

    async def index_existing_story_files(
        self, prompt_file_path: Path, output_dir: Path
    ) -> Dict[str, int]:
        """Index existing story files from output directory."""
        story_name = await self.initialize_story(
            str(prompt_file_path), prompt_file_path.stem
        )

        indexing_results: Dict[str, int] = {}

        # Look for existing output files
        if output_dir.exists():
            # Index chapter files
            chapter_files = list(output_dir.glob("Chapter*.md"))
            for chapter_file in chapter_files:
                try:
                    chapter_content = chapter_file.read_text(encoding="utf-8")
                    chapter_number = self._extract_chapter_number(chapter_file.name)

                    chunk_ids = await self.index_chapter(
                        chapter_content, chapter_number, chapter_file.stem
                    )
                    indexing_results[f"Chapter {chapter_number}"] = len(chunk_ids)

                except Exception as e:
                    logger.error(f"Failed to index chapter file {chapter_file}: {e}")

            # Index character files
            character_files = list(output_dir.glob("*Character*.md"))
            for char_file in character_files:
                try:
                    char_content = char_file.read_text(encoding="utf-8")
                    character_name = char_file.stem.replace("Character", "").strip()

                    chunk_ids = await self.index_character(char_content, character_name)
                    indexing_results[f"Character: {character_name}"] = len(chunk_ids)

                except Exception as e:
                    logger.error(f"Failed to index character file {char_file}: {e}")

        logger.info(f"Indexed existing story files for story '{story_name}'")
        return indexing_results

    def _extract_chapter_number(self, filename: str) -> int:
        """Extract chapter number from filename."""
        import re

        match = re.search(r"Chapter\s*(\d+)", filename, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return 1  # Default to chapter 1 if no number found

    async def close(self):
        """Close the RAG integration service (no-op for ChromaDB)."""
        pass
