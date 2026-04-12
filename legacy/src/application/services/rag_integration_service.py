"""RAG integration service for story generation pipeline."""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from application.services.rag_service import RAGService
from application.services.content_chunker import ContentChunker, ContentChunk

logger = logging.getLogger(__name__)


class RAGIntegrationService:
    """Service for integrating RAG capabilities with the story generation pipeline."""
    
    def __init__(self, rag_service: RAGService, content_chunker: ContentChunker):
        self.rag_service = rag_service
        self.content_chunker = content_chunker
        self._story_cache: Dict[str, int] = {}  # story_identifier -> story_id
        self._current_story_identifier: Optional[str] = None
    
    def set_current_story_identifier(self, story_identifier: str) -> None:
        """Set the current story identifier for RAG operations."""
        self._current_story_identifier = story_identifier
        logger.info(f"Set current story identifier: {story_identifier}")
    
    def get_current_story_identifier(self) -> Optional[str]:
        """Get the current story identifier."""
        return self._current_story_identifier
    
    async def initialize_story(self, story_identifier: str, story_name: Optional[str] = None) -> int:
        """Initialize a story in the RAG system using a story identifier."""
        if not story_name:
            story_name = story_identifier
        
        # Check cache first
        if story_identifier in self._story_cache:
            return self._story_cache[story_identifier]
        
        # Create or get story from database
        from pathlib import Path
        story_id = await self.rag_service.create_story(story_name, Path(story_identifier))
        self._story_cache[story_identifier] = story_id
        
        logger.info(f"Initialized story '{story_name}' with ID {story_id}")
        return story_id
    
    async def _get_or_create_story_id(self, story_identifier: Optional[str] = None) -> int:
        """Get or create a story ID for the given identifier."""
        # Ensure RAG service is initialized
        if not hasattr(self.rag_service, '_initialized'):
            await self.rag_service.initialize()
            self.rag_service._initialized = True
        
        identifier = story_identifier or self._current_story_identifier
        if not identifier:
            raise ValueError("No story identifier available for RAG operations")
        
        return await self.initialize_story(identifier)
    
    async def cleanup_content_by_type_and_metadata(
        self,
        content_type: str,
        metadata_filters: Optional[Dict[str, Any]] = None,
        story_identifier: Optional[str] = None
    ) -> int:
        """Clean up content chunks by type and metadata before re-indexing."""
        try:
            story_id = await self._get_or_create_story_id(story_identifier)
            deleted_count = await self.rag_service.delete_content_by_type_and_metadata(
                story_id, content_type, metadata_filters
            )
            logger.info(f"Cleaned up {deleted_count} {content_type} chunks for story {story_id}")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to cleanup {content_type} content: {e}")
            raise
    
    async def index_outline(
        self,
        outline_content: str,
        chapter_number: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        story_identifier: Optional[str] = None
    ) -> List[int]:
        """Index story outline content."""
        story_id = await self._get_or_create_story_id(story_identifier)
        
        # Chunk the outline content
        chunks = self.content_chunker.chunk_text(
            outline_content,
            "outline",
            "story_outline",
            f"Outline - Chapter {chapter_number}" if chapter_number else "Story Outline",
            metadata or {},
            chapter_number
        )
        
        # Index each chunk
        chunk_ids = []
        for chunk in chunks:
            chunk_id = await self.rag_service.index_content(
                story_id=story_id,
                content_type=chunk.chunk_type,
                content=chunk.content,
                metadata=chunk.metadata,
                title=chunk.title,
                content_subtype=chunk.chunk_subtype,
                chapter_number=chunk.chapter_number,
                scene_number=chunk.scene_number
            )
            chunk_ids.append(chunk_id)
        
        logger.info(f"Indexed {len(chunks)} outline chunks for story {story_id}")
        return chunk_ids
    
    async def index_chapter(
        self,
        chapter_content: str,
        chapter_number: int,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        story_identifier: Optional[str] = None
    ) -> List[int]:
        """Index chapter content."""
        story_id = await self._get_or_create_story_id(story_identifier)
        
        # Chunk the chapter content
        chunks = self.content_chunker.chunk_chapter(
            chapter_content,
            chapter_number,
            title,
            metadata or {}
        )
        
        # Index each chunk
        chunk_ids = []
        for chunk in chunks:
            chunk_id = await self.rag_service.index_content(
                story_id=story_id,
                content_type=chunk.chunk_type,
                content=chunk.content,
                metadata=chunk.metadata,
                title=chunk.title,
                content_subtype=chunk.chunk_subtype,
                chapter_number=chunk.chapter_number,
                scene_number=chunk.scene_number
            )
            chunk_ids.append(chunk_id)
        
        logger.info(f"Indexed {len(chunks)} chapter chunks for story {story_id}, chapter {chapter_number}")
        return chunk_ids
    
    async def index_character(
        self,
        character_content: str,
        character_name: str,
        metadata: Optional[Dict[str, Any]] = None,
        story_identifier: Optional[str] = None
    ) -> List[int]:
        """Index character information."""
        story_id = await self._get_or_create_story_id(story_identifier)
        
        # Chunk the character content
        chunks = self.content_chunker.chunk_character_sheet(
            character_content,
            character_name,
            metadata or {}
        )
        
        # Index each chunk
        chunk_ids = []
        for chunk in chunks:
            chunk_id = await self.rag_service.index_content(
                story_id=story_id,
                content_type=chunk.chunk_type,
                content=chunk.content,
                metadata=chunk.metadata,
                title=chunk.title,
                content_subtype=chunk.chunk_subtype
            )
            chunk_ids.append(chunk_id)
        
        logger.info(f"Indexed {len(chunks)} character chunks for '{character_name}' in story {story_id}")
        return chunk_ids
    
    async def index_setting(
        self,
        setting_content: str,
        location_name: str,
        metadata: Optional[Dict[str, Any]] = None,
        story_identifier: Optional[str] = None
    ) -> List[int]:
        """Index setting information."""
        story_id = await self._get_or_create_story_id(story_identifier)
        
        # Chunk the setting content
        chunks = self.content_chunker.chunk_setting_description(
            setting_content,
            location_name,
            metadata or {}
        )
        
        # Index each chunk
        chunk_ids = []
        for chunk in chunks:
            chunk_id = await self.rag_service.index_content(
                story_id=story_id,
                content_type=chunk.chunk_type,
                content=chunk.content,
                metadata=chunk.metadata,
                title=chunk.title,
                content_subtype=chunk.chunk_subtype
            )
            chunk_ids.append(chunk_id)
        
        logger.info(f"Indexed {len(chunks)} setting chunks for '{location_name}' in story {story_id}")
        return chunk_ids
    
    async def index_event(
        self,
        event_content: str,
        event_type: str,
        chapter_number: Optional[int] = None,
        scene_number: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        story_identifier: Optional[str] = None
    ) -> int:
        """Index an event or recap."""
        story_id = await self._get_or_create_story_id(story_identifier)
        
        event_metadata = metadata or {}
        event_metadata["event_type"] = event_type
        
        chunk_id = await self.rag_service.index_content(
            story_id=story_id,
            content_type="event",
            content=event_content,
            metadata=event_metadata,
            title=f"Event: {event_type}",
            content_subtype="story_event",
            chapter_number=chapter_number,
            scene_number=scene_number
        )
        
        logger.info(f"Indexed event '{event_type}' for story {story_id}")
        return chunk_id
    
    async def get_generation_context(
        self,
        chapter_number: int,
        scene_number: Optional[int] = None,
        content_types: Optional[List[str]] = None,
        story_identifier: Optional[str] = None
    ) -> str:
        """Get relevant context for story generation."""
        story_id = await self._get_or_create_story_id(story_identifier)
        
        context = await self.rag_service.get_context_for_generation(
            story_id=story_id,
            chapter_number=chapter_number,
            scene_number=scene_number,
            content_types=content_types
        )
        
        logger.debug(f"Retrieved context for story {story_id}, chapter {chapter_number}")
        return context
    
    async def search_story_content(
        self,
        query: str,
        content_type: Optional[str] = None,
        limit: Optional[int] = None,
        story_identifier: Optional[str] = None
    ) -> List[tuple]:
        """Search for content in a story."""
        story_id = await self._get_or_create_story_id(story_identifier)
        
        results = await self.rag_service.search_similar(
            story_id=story_id,
            query=query,
            content_type=content_type,
            limit=limit
        )
        
        logger.debug(f"Found {len(results)} results for query in story {story_id}")
        return results
    
    async def get_story_summary(self, story_identifier: Optional[str] = None) -> Dict[str, Any]:
        """Get a summary of the story's indexed content."""
        story_id = await self._get_or_create_story_id(story_identifier)
        
        summary = await self.rag_service.get_story_summary(story_id)
        logger.info(f"Retrieved summary for story {story_id}")
        return summary
    
    # Legacy methods for backward compatibility
    async def index_outline_with_path(
        self,
        prompt_file_path: Path,
        outline_content: str,
        chapter_number: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[int]:
        """Legacy method: Index story outline content with prompt file path."""
        logger.warning("index_outline_with_path is deprecated. Use index_outline instead.")
        return await self.index_outline(outline_content, chapter_number, metadata, str(prompt_file_path))
    
    async def index_chapter_with_path(
        self,
        prompt_file_path: Path,
        chapter_content: str,
        chapter_number: int,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[int]:
        """Legacy method: Index chapter content with prompt file path."""
        logger.warning("index_chapter_with_path is deprecated. Use index_chapter instead.")
        return await self.index_chapter(chapter_content, chapter_number, title, metadata, str(prompt_file_path))
    
    async def index_character_with_path(
        self,
        prompt_file_path: Path,
        character_content: str,
        character_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[int]:
        """Legacy method: Index character information with prompt file path."""
        logger.warning("index_character_with_path is deprecated. Use index_character instead.")
        return await self.index_character(character_content, character_name, metadata, str(prompt_file_path))
    
    async def index_setting_with_path(
        self,
        prompt_file_path: Path,
        setting_content: str,
        location_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[int]:
        """Legacy method: Index setting information with prompt file path."""
        logger.warning("index_setting_with_path is deprecated. Use index_setting instead.")
        return await self.index_setting(setting_content, location_name, metadata, str(prompt_file_path))
    
    async def index_event_with_path(
        self,
        prompt_file_path: Path,
        event_content: str,
        event_type: str,
        chapter_number: Optional[int] = None,
        scene_number: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Legacy method: Index an event or recap with prompt file path."""
        logger.warning("index_event_with_path is deprecated. Use index_event instead.")
        return await self.index_event(event_content, event_type, chapter_number, scene_number, metadata, str(prompt_file_path))
    
    async def get_generation_context_with_path(
        self,
        prompt_file_path: Path,
        chapter_number: int,
        scene_number: Optional[int] = None,
        content_types: Optional[List[str]] = None
    ) -> str:
        """Legacy method: Get relevant context for story generation with prompt file path."""
        logger.warning("get_generation_context_with_path is deprecated. Use get_generation_context instead.")
        return await self.get_generation_context(chapter_number, scene_number, content_types, str(prompt_file_path))
    
    async def search_story_content_with_path(
        self,
        prompt_file_path: Path,
        query: str,
        content_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[tuple]:
        """Legacy method: Search for content in a story with prompt file path."""
        logger.warning("search_story_content_with_path is deprecated. Use search_story_content instead.")
        return await self.search_story_content(query, content_type, limit, str(prompt_file_path))
    
    async def get_story_summary_with_path(self, prompt_file_path: Path) -> Dict[str, Any]:
        """Legacy method: Get a summary of the story's indexed content with prompt file path."""
        logger.warning("get_story_summary_with_path is deprecated. Use get_story_summary instead.")
        return await self.get_story_summary(str(prompt_file_path))
    
    async def index_existing_story_files(
        self,
        prompt_file_path: Path,
        output_dir: Path
    ) -> Dict[str, int]:
        """Index existing story files from output directory."""
        story_id = await self.initialize_story(str(prompt_file_path), prompt_file_path.stem)
        
        indexing_results = {}
        
        # Look for existing output files
        if output_dir.exists():
            # Index chapter files
            chapter_files = list(output_dir.glob("Chapter*.md"))
            for chapter_file in chapter_files:
                try:
                    chapter_content = chapter_file.read_text(encoding='utf-8')
                    chapter_number = self._extract_chapter_number(chapter_file.name)
                    
                    chunk_ids = await self.index_chapter(
                        chapter_content,
                        chapter_number,
                        chapter_file.stem
                    )
                    indexing_results[f"Chapter {chapter_number}"] = len(chunk_ids)
                    
                except Exception as e:
                    logger.error(f"Failed to index chapter file {chapter_file}: {e}")
            
            # Index character files
            character_files = list(output_dir.glob("*Character*.md"))
            for char_file in character_files:
                try:
                    char_content = char_file.read_text(encoding='utf-8')
                    character_name = char_file.stem.replace("Character", "").strip()
                    
                    chunk_ids = await self.index_character(
                        char_content,
                        character_name
                    )
                    indexing_results[f"Character: {character_name}"] = len(chunk_ids)
                    
                except Exception as e:
                    logger.error(f"Failed to index character file {char_file}: {e}")
        
        logger.info(f"Indexed existing story files for story {story_id}")
        return indexing_results
    
    def _extract_chapter_number(self, filename: str) -> int:
        """Extract chapter number from filename."""
        import re
        match = re.search(r'Chapter\s*(\d+)', filename, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return 1  # Default to chapter 1 if no number found
    
    async def close(self):
        """Close the RAG integration service."""
        await self.rag_service.close()
