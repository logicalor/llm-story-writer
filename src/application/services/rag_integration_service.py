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
        self._story_cache: Dict[str, int] = {}  # prompt_file -> story_id
    
    async def initialize_story(self, prompt_file_path: Path, story_name: Optional[str] = None) -> int:
        """Initialize a story in the RAG system."""
        if not story_name:
            story_name = prompt_file_path.stem
        
        # Check cache first
        cache_key = str(prompt_file_path)
        if cache_key in self._story_cache:
            return self._story_cache[cache_key]
        
        # Create or get story from database
        story_id = await self.rag_service.create_story(story_name, prompt_file_path)
        self._story_cache[cache_key] = story_id
        
        logger.info(f"Initialized story '{story_name}' with ID {story_id}")
        return story_id
    
    async def index_outline(
        self,
        prompt_file_path: Path,
        outline_content: str,
        chapter_number: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[int]:
        """Index story outline content."""
        story_id = await self.initialize_story(prompt_file_path)
        
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
        prompt_file_path: Path,
        chapter_content: str,
        chapter_number: int,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[int]:
        """Index chapter content."""
        story_id = await self.initialize_story(prompt_file_path)
        
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
        prompt_file_path: Path,
        character_content: str,
        character_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[int]:
        """Index character information."""
        story_id = await self.initialize_story(prompt_file_path)
        
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
        prompt_file_path: Path,
        setting_content: str,
        location_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[int]:
        """Index setting information."""
        story_id = await self.initialize_story(prompt_file_path)
        
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
        prompt_file_path: Path,
        event_content: str,
        event_type: str,
        chapter_number: Optional[int] = None,
        scene_number: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Index an event or recap."""
        story_id = await self.initialize_story(prompt_file_path)
        
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
        prompt_file_path: Path,
        chapter_number: int,
        scene_number: Optional[int] = None,
        content_types: Optional[List[str]] = None
    ) -> str:
        """Get relevant context for story generation."""
        story_id = await self.initialize_story(prompt_file_path)
        
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
        prompt_file_path: Path,
        query: str,
        content_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[tuple]:
        """Search for content in a story."""
        story_id = await self.initialize_story(prompt_file_path)
        
        results = await self.rag_service.search_similar(
            story_id=story_id,
            query=query,
            content_type=content_type,
            limit=limit
        )
        
        logger.debug(f"Found {len(results)} results for query in story {story_id}")
        return results
    
    async def get_story_summary(self, prompt_file_path: Path) -> Dict[str, Any]:
        """Get a summary of the story's indexed content."""
        story_id = await self.initialize_story(prompt_file_path)
        
        summary = await self.rag_service.get_story_summary(story_id)
        logger.info(f"Retrieved summary for story {story_id}")
        return summary
    
    async def index_existing_story_files(
        self,
        prompt_file_path: Path,
        output_dir: Path
    ) -> Dict[str, int]:
        """Index existing story files from output directory."""
        story_id = await self.initialize_story(prompt_file_path)
        
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
                        prompt_file_path,
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
                        prompt_file_path,
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
