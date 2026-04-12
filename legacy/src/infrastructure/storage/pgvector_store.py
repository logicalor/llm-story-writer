"""PostgreSQL vector store implementation using pgvector."""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
import asyncpg
from pgvector.asyncpg import register_vector
from domain.exceptions import StorageError

logger = logging.getLogger(__name__)


class PgVectorStore:
    """PostgreSQL vector store using pgvector extension."""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._pool: Optional[asyncpg.Pool] = None
    
    async def initialize(self):
        """Initialize the connection pool and ensure tables exist."""
        try:
            self._pool = await asyncpg.create_pool(self.connection_string)
            
            # Register vector type handler
            await self._register_vector_type()
            
            await self._ensure_tables_exist()
            logger.info("PgVector store initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize PgVector store: {e}")
            raise StorageError(f"Failed to initialize PgVector store: {e}")
    
    async def _register_vector_type(self):
        """Register the vector type handler with asyncpg using pgvector.asyncpg."""
        logger.info("Using pgvector.asyncpg for vector handling")
        try:
            # Try to register the vector type handler on the pool itself
            await register_vector(self._pool)
            logger.info("Vector type handler registered successfully on pool")
        except Exception as e:
            logger.warning(f"Failed to register vector type handler on pool: {e}")
            # Fallback: try to register on a connection
            try:
                async with self._pool.acquire() as conn:
                    await register_vector(conn)
                    logger.info("Vector type handler registered successfully on connection")
            except Exception as conn_e:
                logger.warning(f"Failed to register vector type handler on connection: {conn_e}")
                
        # Additional fallback: manually register the type handler
        try:
            async with self._pool.acquire() as conn:
                # Check if vector type is already registered
                type_info = await conn.fetchval(
                    "SELECT oid FROM pg_type WHERE typname = 'vector'"
                )
                if type_info:
                    logger.info(f"Vector type found in database with OID: {type_info}")
                else:
                    logger.warning("Vector type not found in database")
                    
                # Try to manually register the type handler
                from pgvector.asyncpg import register_vector
                await register_vector(conn)
                logger.info("Vector type handler manually registered on connection")
        except Exception as manual_e:
            logger.warning(f"Failed to manually register vector type handler: {manual_e}")
    
    async def close(self):
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
    
    async def _ensure_tables_exist(self):
        """Ensure required tables exist."""
        async with self._pool.acquire() as conn:
            # Check if vector extension exists
            result = await conn.fetchval(
                "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
            )
            if not result:
                raise StorageError("pgvector extension not found. Please install it first.")
            
            # Check if stories table exists
            result = await conn.fetchval(
                "SELECT 1 FROM information_schema.tables WHERE table_name = 'stories'"
            )
            if not result:
                raise StorageError("Stories table not found. Please run init.sql first.")
    
    async def create_story(self, story_name: str, prompt_file_name: str) -> int:
        """Create a new story and return its ID."""
        async with self._pool.acquire() as conn:
            try:
                story_id = await conn.fetchval(
                    """
                    INSERT INTO stories (story_name, prompt_file_name)
                    VALUES ($1, $2)
                    RETURNING id
                    """,
                    story_name, prompt_file_name
                )
                logger.info(f"Created story '{story_name}' with ID {story_id}")
                return story_id
            except asyncpg.UniqueViolationError:
                # Story already exists, get its ID
                story_id = await conn.fetchval(
                    "SELECT id FROM stories WHERE story_name = $1",
                    story_name
                )
                logger.info(f"Story '{story_name}' already exists with ID {story_id}")
                return story_id
            except Exception as e:
                logger.error(f"Failed to create story: {e}")
                raise StorageError(f"Failed to create story: {e}")
    
    async def store_embedding(
        self,
        story_id: int,
        content_type: str,
        content: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
        title: Optional[str] = None,
        content_subtype: Optional[str] = None,
        chapter_number: Optional[int] = None,
        scene_number: Optional[int] = None
    ) -> int:
        """Store content with embedding in the vector store."""
        async with self._pool.acquire() as conn:
            try:
                # Debug logging to check embedding type at this point
                logger.debug(f"store_embedding received embedding type: {type(embedding)}, length: {len(embedding) if isinstance(embedding, list) else 'N/A'}")
                logger.debug(f"store_embedding embedding preview: {str(embedding)[:100]}...")
                
                # Pass embedding list directly - PostgreSQL will handle the conversion
                chunk_id = await conn.fetchval(
                    """
                    INSERT INTO content_chunks 
                    (story_id, content_type, content_subtype, title, content, metadata, 
                     embedding, chapter_number, scene_number)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    RETURNING id
                    """,
                    story_id, content_type, content_subtype, title, content,
                    json.dumps(metadata) if metadata else None,
                    embedding, chapter_number, scene_number
                )
                logger.debug(f"Stored embedding for content type '{content_type}' with ID {chunk_id}")
                return chunk_id
            except Exception as e:
                logger.error(f"Failed to store embedding: {e}")
                raise StorageError(f"Failed to store embedding: {e}")
    
    async def search_similar(
        self,
        query_embedding: List[float],
        story_id: Optional[int] = None,
        content_type: Optional[str] = None,
        limit: int = 10,
        similarity_threshold: float = 0.7,
        use_hnsw: bool = True
    ) -> List[Tuple[int, str, str, Dict[str, Any], float]]:
        """
        Search for similar content using vector similarity.
        
        Returns:
            List of tuples: (chunk_id, content_type, content, metadata, similarity_score)
        """
        async with self._pool.acquire() as conn:
            try:
                # Build the query based on parameters
                query_parts = [
                    "SELECT id, content_type, content, metadata, 1 - (embedding <=> $1) as similarity"
                ]
                query_parts.append("FROM content_chunks")
                
                params = [query_embedding]
                param_count = 1
                
                if story_id:
                    query_parts.append("WHERE story_id = $2")
                    params.append(story_id)
                    param_count = 2
                else:
                    query_parts.append("WHERE 1=1")  # Always true condition for cross-story search
                
                if content_type:
                    param_count += 1
                    query_parts.append(f"AND content_type = ${param_count}")
                    params.append(content_type)
                
                query_parts.append(f"AND 1 - (embedding <=> $1) >= ${param_count + 1}")
                param_count += 1
                params.append(similarity_threshold)
                
                # Choose index based on preference
                if use_hnsw:
                    query_parts.append("ORDER BY embedding <=> $1")
                else:
                    query_parts.append("ORDER BY embedding <=> $1")
                
                query_parts.append(f"LIMIT ${param_count + 1}")
                params.append(limit)
                
                query = " ".join(query_parts)
                
                rows = await conn.fetch(query, *params)
                
                results = []
                for row in rows:
                    metadata = json.loads(row['metadata']) if row['metadata'] else {}
                    results.append((
                        row['id'],
                        row['content_type'],
                        row['content'],
                        metadata,
                        row['similarity']
                    ))
                
                logger.debug(f"Found {len(results)} similar content chunks")
                return results
                
            except Exception as e:
                logger.error(f"Failed to search similar content: {e}")
                raise StorageError(f"Failed to search similar content: {e}")
    
    async def get_story_content(
        self,
        story_id: int,
        content_type: Optional[str] = None,
        chapter_number: Optional[int] = None,
        scene_number: Optional[int] = None
    ) -> List[Tuple[int, str, str, Dict[str, Any]]]:
        """Get content chunks for a story with optional filtering."""
        async with self._pool.acquire() as conn:
            try:
                query_parts = [
                    "SELECT id, content_type, content, metadata"
                ]
                query_parts.append("FROM content_chunks")
                query_parts.append("WHERE story_id = $1")
                
                params = [story_id]
                param_count = 1
                
                if content_type:
                    param_count += 1
                    query_parts.append(f"AND content_type = ${param_count}")
                    params.append(content_type)
                
                if chapter_number is not None:
                    param_count += 1
                    query_parts.append(f"AND chapter_number = ${param_count}")
                    params.append(chapter_number)
                
                if scene_number is not None:
                    param_count += 1
                    query_parts.append(f"AND scene_number = ${param_count}")
                    params.append(scene_number)
                
                query_parts.append("ORDER BY created_at")
                
                query = " ".join(query_parts)
                
                rows = await conn.fetch(query, *params)
                
                results = []
                for row in rows:
                    metadata = json.loads(row['metadata']) if row['metadata'] else {}
                    results.append((
                        row['id'],
                        row['content_type'],
                        row['content'],
                        metadata
                    ))
                
                return results
                
            except Exception as e:
                logger.error(f"Failed to get story content: {e}")
                raise StorageError(f"Failed to get story content: {e}")
    
    async def delete_content_by_type_and_metadata(
        self,
        story_id: int,
        content_type: str,
        metadata_filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """Delete content chunks by type and optional metadata filters."""
        async with self._pool.acquire() as conn:
            try:
                # First, count the chunks that will be deleted
                count_query_parts = [
                    "SELECT COUNT(*) FROM content_chunks WHERE story_id = $1 AND content_type = $2"
                ]
                count_params = [story_id, content_type]
                param_count = 2
                
                # Add metadata filters if provided
                if metadata_filters:
                    for key, value in metadata_filters.items():
                        param_count += 1
                        count_query_parts.append(f"AND metadata->>'{key}' = ${param_count}")
                        count_params.append(str(value))
                
                count_query = " ".join(count_query_parts)
                chunk_count = await conn.fetchval(count_query, *count_params)
                
                # Now delete the chunks
                delete_query_parts = [
                    "DELETE FROM content_chunks WHERE story_id = $1 AND content_type = $2"
                ]
                delete_params = [story_id, content_type]
                param_count = 2
                
                # Add metadata filters if provided
                if metadata_filters:
                    for key, value in metadata_filters.items():
                        param_count += 1
                        delete_query_parts.append(f"AND metadata->>'{key}' = ${param_count}")
                        delete_params.append(str(value))
                
                delete_query = " ".join(delete_query_parts)
                await conn.execute(delete_query, *delete_params)
                
                logger.info(f"Deleted {chunk_count} {content_type} chunks for story {story_id}")
                return chunk_count
                
            except Exception as e:
                logger.error(f"Failed to delete {content_type} content for story {story_id}: {e}")
                raise StorageError(f"Failed to delete {content_type} content for story {story_id}: {e}")
    
    async def delete_story_content(self, story_id: int) -> int:
        """Delete all content for a story."""
        async with self._pool.acquire() as conn:
            try:
                # Return deleted row IDs and count them client-side
                rows = await conn.fetch(
                    "DELETE FROM content_chunks WHERE story_id = $1 RETURNING id",
                    story_id
                )
                deleted_count = len(rows)
                logger.info(f"Deleted {deleted_count} content chunks for story {story_id}")
                return deleted_count
            except Exception as e:
                logger.error(f"Failed to delete story content: {e}")
                raise StorageError(f"Failed to delete story content: {e}")
    
    async def get_story_info(self, story_id: int) -> Optional[Dict[str, Any]]:
        """Get information about a story."""
        async with self._pool.acquire() as conn:
            try:
                row = await conn.fetchrow(
                    "SELECT * FROM stories WHERE id = $1",
                    story_id
                )
                if row:
                    return dict(row)
                return None
            except Exception as e:
                logger.error(f"Failed to get story info: {e}")
                raise StorageError(f"Failed to get story info: {e}")
    
    async def list_stories(self) -> List[Dict[str, Any]]:
        """List all stories."""
        async with self._pool.acquire() as conn:
            try:
                rows = await conn.fetch("SELECT * FROM stories ORDER BY created_at DESC")
                return [dict(row) for row in rows]
            except Exception as e:
                logger.error(f"Failed to list stories: {e}")
                raise StorageError(f"Failed to list stories: {e}")
