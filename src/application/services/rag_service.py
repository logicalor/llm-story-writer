"""RAG (Retrieval-Augmented Generation) service for story content management."""

import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from infrastructure.providers.ollama_embedding_provider import OllamaEmbeddingProvider
from infrastructure.storage.pgvector_store import PgVectorStore
from domain.exceptions import StorageError

logger = logging.getLogger(__name__)


class RAGService:
    """RAG service for managing story content with vector embeddings."""
    
    def __init__(
        self,
        embedding_provider: OllamaEmbeddingProvider,
        vector_store: PgVectorStore,
        similarity_threshold: float = 0.7,
        max_context_chunks: int = 20
    ):
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
        self.similarity_threshold = similarity_threshold
        self.max_context_chunks = max_context_chunks
    
    async def initialize(self):
        """Initialize the RAG service."""
        try:
            await self.vector_store.initialize()
            logger.info("RAG service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RAG service: {e}")
            raise
    
    async def close(self):
        """Close the RAG service."""
        await self.vector_store.close()
    
    async def create_story(self, story_name: str, prompt_file_path: Path) -> int:
        """Create a new story in the RAG system."""
        prompt_file_name = prompt_file_path.name
        story_id = await self.vector_store.create_story(story_name, prompt_file_name)
        logger.info(f"Created story '{story_name}' with ID {story_id}")
        return story_id
    
    async def index_content(
        self,
        story_id: int,
        content_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        title: Optional[str] = None,
        content_subtype: Optional[str] = None,
        chapter_number: Optional[int] = None,
        scene_number: Optional[int] = None
    ) -> int:
        """Index content by generating embeddings and storing in vector database."""
        try:
            # Generate embedding for the content
            embedding = await self.embedding_provider.get_single_embedding(content)
            
            # Store in vector database
            chunk_id = await self.vector_store.store_embedding(
                story_id=story_id,
                content_type=content_type,
                content=content,
                embedding=embedding,
                metadata=metadata,
                title=title,
                content_subtype=content_subtype,
                chapter_number=chapter_number,
                scene_number=scene_number
            )
            
            logger.debug(f"Indexed content type '{content_type}' with ID {chunk_id}")
            return chunk_id
            
        except Exception as e:
            logger.error(f"Failed to index content: {e}")
            raise StorageError(f"Failed to index content: {e}")
    
    async def search_similar(
        self,
        story_id: int,
        query: str,
        content_type: Optional[str] = None,
        limit: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
        use_hnsw: bool = True
    ) -> List[Tuple[int, str, str, Dict[str, Any], float]]:
        """Search for similar content using text query."""
        try:
            # Generate embedding for the query
            query_embedding = await self.embedding_provider.get_single_embedding(query)
            
            # Search for similar content
            limit = limit or self.max_context_chunks
            threshold = similarity_threshold or self.similarity_threshold
            
            results = await self.vector_store.search_similar(
                story_id=story_id,
                query_embedding=query_embedding,
                content_type=content_type,
                limit=limit,
                similarity_threshold=threshold,
                use_hnsw=use_hnsw
            )
            
            logger.debug(f"Found {len(results)} similar content chunks for query")
            return results
            
        except Exception as e:
            logger.error(f"Failed to search similar content: {e}")
            raise StorageError(f"Failed to search similar content: {e}")
    
    async def get_context_for_generation(
        self,
        story_id: int,
        chapter_number: int,
        scene_number: Optional[int] = None,
        content_types: Optional[List[str]] = None
    ) -> str:
        """Get relevant context for story generation."""
        try:
            context_parts = []
            
            # Get character information
            if not content_types or "character" in content_types:
                character_context = await self._get_character_context(story_id, chapter_number)
                if character_context:
                    context_parts.append("CHARACTER CONTEXT:\n" + character_context)
            
            # Get setting information
            if not content_types or "setting" in content_types:
                setting_context = await self._get_setting_context(story_id, chapter_number)
                if setting_context:
                    context_parts.append("SETTING CONTEXT:\n" + setting_context)
            
            # Get plot context from previous chapters
            if not content_types or "outline" in content_types or "scene" in content_types:
                plot_context = await self._get_plot_context(story_id, chapter_number)
                if plot_context:
                    context_parts.append("PLOT CONTEXT:\n" + plot_context)
            
            # Get recent events
            if not content_types or "event" in content_types:
                event_context = await self._get_event_context(story_id, chapter_number)
                if event_context:
                    context_parts.append("RECENT EVENTS:\n" + event_context)
            
            return "\n\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Failed to get context for generation: {e}")
            return ""
    
    async def _get_character_context(self, story_id: int, chapter_number: int) -> str:
        """Get character context for a specific chapter."""
        try:
            # Get character information from previous chapters
            character_chunks = await self.vector_store.get_story_content(
                story_id=story_id,
                content_type="character",
                chapter_number=chapter_number
            )
            
            if not character_chunks:
                # Fall back to all character information
                character_chunks = await self.vector_store.get_story_content(
                    story_id=story_id,
                    content_type="character"
                )
            
            if character_chunks:
                context_parts = []
                for _, content_type, content, metadata in character_chunks:
                    character_name = metadata.get("character_name", "Unknown")
                    context_parts.append(f"{character_name}: {content}")
                
                return "\n".join(context_parts)
            
            return ""
            
        except Exception as e:
            logger.error(f"Failed to get character context: {e}")
            return ""
    
    async def _get_setting_context(self, story_id: int, chapter_number: int) -> str:
        """Get setting context for a specific chapter."""
        try:
            # Get setting information from previous chapters
            setting_chunks = await self.vector_store.get_story_content(
                story_id=story_id,
                content_type="setting",
                chapter_number=chapter_number
            )
            
            if not setting_chunks:
                # Fall back to all setting information
                setting_chunks = await self.vector_store.get_story_content(
                    story_id=story_id,
                    content_type="setting"
                )
            
            if setting_chunks:
                context_parts = []
                for _, content_type, content, metadata in setting_chunks:
                    location = metadata.get("location", "Unknown")
                    context_parts.append(f"{location}: {content}")
                
                return "\n".join(context_parts)
            
            return ""
            
        except Exception as e:
            logger.error(f"Failed to get setting context: {e}")
            return ""
    
    async def _get_plot_context(self, story_id: int, chapter_number: int) -> str:
        """Get plot context from previous chapters."""
        try:
            # Get outline and scene information from previous chapters
            plot_chunks = await self.vector_store.get_story_content(
                story_id=story_id,
                content_type="outline"
            )
            
            # Filter to relevant chapters
            relevant_chunks = []
            for _, content_type, content, metadata in plot_chunks:
                chunk_chapter = metadata.get("chapter_number")
                if chunk_chapter and chunk_chapter < chapter_number:
                    relevant_chunks.append((chunk_chapter, content))
            
            if relevant_chunks:
                # Sort by chapter number and take the most recent
                relevant_chunks.sort(key=lambda x: x[0])
                recent_chunks = relevant_chunks[-3:]  # Last 3 chapters
                
                context_parts = []
                for chapter_num, content in recent_chunks:
                    context_parts.append(f"Chapter {chapter_num}: {content}")
                
                return "\n".join(context_parts)
            
            return ""
            
        except Exception as e:
            logger.error(f"Failed to get plot context: {e}")
            return ""
    
    async def _get_event_context(self, story_id: int, chapter_number: int) -> str:
        """Get recent event context."""
        try:
            # Get recent events
            event_chunks = await self.vector_store.get_story_content(
                story_id=story_id,
                content_type="event"
            )
            
            if event_chunks:
                # Take the most recent events
                recent_events = event_chunks[-5:]  # Last 5 events
                
                context_parts = []
                for _, content_type, content, metadata in recent_events:
                    event_type = metadata.get("event_type", "Event")
                    context_parts.append(f"{event_type}: {content}")
                
                return "\n".join(context_parts)
            
            return ""
            
        except Exception as e:
            logger.error(f"Failed to get event context: {e}")
            return ""
    
    async def get_story_summary(self, story_id: int) -> Dict[str, Any]:
        """Get a comprehensive summary of a story."""
        try:
            story_info = await self.vector_store.get_story_info(story_id)
            if not story_info:
                return {}
            
            # Get content counts by type
            content_counts = {}
            for content_type in ["character", "setting", "outline", "scene", "event"]:
                chunks = await self.vector_store.get_story_content(
                    story_id=story_id,
                    content_type=content_type
                )
                content_counts[content_type] = len(chunks)
            
            summary = {
                "story_info": story_info,
                "content_counts": content_counts,
                "total_chunks": sum(content_counts.values())
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get story summary: {e}")
            return {}
    
    async def delete_content_by_type_and_metadata(
        self,
        story_id: int,
        content_type: str,
        metadata_filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """Delete content chunks by type and optional metadata filters."""
        try:
            deleted_count = await self.vector_store.delete_content_by_type_and_metadata(
                story_id, content_type, metadata_filters
            )
            logger.info(f"Deleted {deleted_count} {content_type} chunks for story {story_id}")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to delete {content_type} content for story {story_id}: {e}")
            raise
    
    async def delete_story(self, story_id: int) -> bool:
        """Delete a story and all its content."""
        try:
            deleted_count = await self.vector_store.delete_story_content(story_id)
            logger.info(f"Deleted story {story_id} with {deleted_count} content chunks")
            return True
        except Exception as e:
            logger.error(f"Failed to delete story: {e}")
            return False
