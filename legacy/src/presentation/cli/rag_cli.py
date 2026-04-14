"""CLI tool for managing the RAG system."""

import asyncio
import argparse
import logging
from pathlib import Path
from typing import Optional

from ..config.rag_config import RAGConfigLoader, RAGConfig
from ..infrastructure.providers.ollama_embedding_provider import OllamaEmbeddingProvider
from ..infrastructure.storage.pgvector_store import PgVectorStore
from ..application.services.rag_service import RAGService
from ..application.services.content_chunker import ContentChunker
from ..application.services.rag_integration_service import RAGIntegrationService


class RAGCLI:
    """Command-line interface for RAG system management."""
    
    def __init__(self):
        self.rag_service: Optional[RAGService] = None
        self.rag_integration: Optional[RAGIntegrationService] = None
        self.config: Optional[RAGConfig] = None
    
    async def initialize(self):
        """Initialize the RAG system."""
        try:
            # Load configuration
            from ..config.config_loader import ConfigLoader
            main_config_loader = ConfigLoader()
            config_loader = RAGConfigLoader(main_config_loader)
            self.config = config_loader.load_rag_config()
            
            # Validate configuration
            errors = config_loader.validate_config(self.config)
            if errors:
                print("Configuration errors:")
                for error in errors:
                    print(f"  - {error}")
                return False
            
            # Initialize components
            embedding_provider = OllamaEmbeddingProvider(
                host=self.config.ollama_host,
                model=self.config.embedding_model_name
            )
            
            vector_store = PgVectorStore(self.config.connection_string)
            
            self.rag_service = RAGService(
                embedding_provider=embedding_provider,
                vector_store=vector_store,
                similarity_threshold=self.config.similarity_threshold,
                max_context_chunks=self.config.max_context_chunks
            )
            
            content_chunker = ContentChunker(
                max_chunk_size=self.config.max_chunk_size,
                overlap_size=self.config.overlap_size
            )
            
            self.rag_integration = RAGIntegrationService(
                rag_service=self.rag_service,
                content_chunker=content_chunker
            )
            
            # Initialize services
            await self.rag_service.initialize()
            
            print("RAG system initialized successfully!")
            return True
            
        except Exception as e:
            print(f"Failed to initialize RAG system: {e}")
            return False
    
    async def test_connection(self):
        """Test database and embedding model connections."""
        if not self.rag_service:
            print("RAG system not initialized")
            return
        
        print("Testing connections...")
        
        # Test embedding provider
        try:
            connection_ok = await self.rag_service.embedding_provider.test_connection()
            if connection_ok:
                print("✓ Ollama connection: OK")
            else:
                print("✗ Ollama connection: FAILED")
        except Exception as e:
            print(f"✗ Ollama connection: ERROR - {e}")
        
        # Test vector store
        try:
            # Try to get story list as a connection test
            stories = await self.rag_service.vector_store.list_stories()
            print(f"✓ PostgreSQL connection: OK (found {len(stories)} stories)")
        except Exception as e:
            print(f"✗ PostgreSQL connection: ERROR - {e}")
    
    async def list_stories(self):
        """List all stories in the database."""
        if not self.rag_service:
            print("RAG system not initialized")
            return
        
        try:
            stories = await self.rag_service.vector_store.list_stories()
            
            if not stories:
                print("No stories found in database")
                return
            
            print(f"Found {len(stories)} stories:")
            print("-" * 80)
            
            for story in stories:
                print(f"ID: {story['id']}")
                print(f"Name: {story['story_name']}")
                print(f"Prompt File: {story['prompt_file_name']}")
                print(f"Created: {story['created_at']}")
                print(f"Updated: {story['updated_at']}")
                print("-" * 80)
                
        except Exception as e:
            print(f"Failed to list stories: {e}")
    
    async def index_story(self, prompt_file_path: str, output_dir: str):
        """Index an existing story from output directory."""
        if not self.rag_integration:
            print("RAG system not initialized")
            return
        
        prompt_path = Path(prompt_file_path)
        output_path = Path(output_dir)
        
        if not prompt_path.exists():
            print(f"Prompt file not found: {prompt_file_path}")
            return
        
        if not output_path.exists():
            print(f"Output directory not found: {output_dir}")
            return
        
        try:
            print(f"Indexing story from {prompt_file_path}...")
            
            results = await self.rag_integration.index_existing_story_files(
                prompt_path, output_path
            )
            
            print("Indexing completed!")
            print("Results:")
            for item, count in results.items():
                print(f"  {item}: {count} chunks")
                
        except Exception as e:
            print(f"Failed to index story: {e}")
    
    async def search_content(self, prompt_file_path: str, query: str, content_type: Optional[str] = None):
        """Search for content in a story."""
        if not self.rag_integration:
            print("RAG system not initialized")
            return
        
        prompt_path = Path(prompt_file_path)
        
        if not prompt_path.exists():
            print(f"Prompt file not found: {prompt_file_path}")
            return
        
        try:
            print(f"Searching for: '{query}'")
            if content_type:
                print(f"Content type: {content_type}")
            
            results = await self.rag_integration.search_story_content(
                prompt_path, query, content_type
            )
            
            if not results:
                print("No results found")
                return
            
            print(f"Found {len(results)} results:")
            print("-" * 80)
            
            for i, (chunk_id, content_type, content, metadata, similarity) in enumerate(results, 1):
                print(f"Result {i} (ID: {chunk_id}, Similarity: {similarity:.3f})")
                print(f"Type: {content_type}")
                if metadata:
                    print(f"Metadata: {metadata}")
                print(f"Content: {content[:200]}...")
                print("-" * 80)
                
        except Exception as e:
            print(f"Failed to search content: {e}")
    
    async def get_context(self, prompt_file_path: str, chapter_number: int, scene_number: Optional[int] = None):
        """Get generation context for a chapter/scene."""
        if not self.rag_integration:
            print("RAG system not initialized")
            return
        
        prompt_path = Path(prompt_file_path)
        
        if not prompt_path.exists():
            print(f"Prompt file not found: {prompt_file_path}")
            return
        
        try:
            print(f"Getting context for Chapter {chapter_number}")
            if scene_number:
                print(f"Scene {scene_number}")
            
            context = await self.rag_integration.get_generation_context(
                prompt_path, chapter_number, scene_number
            )
            
            if not context:
                print("No context found")
                return
            
            print("Context retrieved:")
            print("=" * 80)
            print(context)
            print("=" * 80)
            
        except Exception as e:
            print(f"Failed to get context: {e}")
    
    async def get_story_summary(self, prompt_file_path: str):
        """Get a summary of a story's indexed content."""
        if not self.rag_integration:
            print("RAG system not initialized")
            return
        
        prompt_path = Path(prompt_file_path)
        
        if not prompt_path.exists():
            print(f"Prompt file not found: {prompt_file_path}")
            return
        
        try:
            print(f"Getting summary for story: {prompt_file_path}")
            
            summary = await self.rag_integration.get_story_summary(prompt_path)
            
            if not summary:
                print("No summary available")
                return
            
            print("Story Summary:")
            print("=" * 80)
            
            story_info = summary.get("story_info", {})
            if story_info:
                print(f"Story ID: {story_info.get('id')}")
                print(f"Story Name: {story_info.get('story_name')}")
                print(f"Prompt File: {story_info.get('prompt_file_name')}")
                print(f"Created: {story_info.get('created_at')}")
                print()
            
            content_counts = summary.get("content_counts", {})
            if content_counts:
                print("Content Counts:")
                for content_type, count in content_counts.items():
                    print(f"  {content_type}: {count}")
                print()
            
            total_chunks = summary.get("total_chunks", 0)
            print(f"Total Content Chunks: {total_chunks}")
            print("=" * 80)
            
        except Exception as e:
            print(f"Failed to get story summary: {e}")
    
    async def close(self):
        """Close the RAG system."""
        if self.rag_integration:
            await self.rag_integration.close()


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="RAG System Management CLI")
    parser.add_argument("command", choices=[
        "test", "list", "index", "search", "context", "summary"
    ], help="Command to execute")
    
    parser.add_argument("--prompt-file", "-p", help="Path to prompt file")
    parser.add_argument("--output-dir", "-o", help="Path to output directory")
    parser.add_argument("--query", "-q", help="Search query")
    parser.add_argument("--content-type", "-t", help="Content type filter")
    parser.add_argument("--chapter", "-c", type=int, help="Chapter number")
    parser.add_argument("--scene", "-s", type=int, help="Scene number")
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize CLI
    cli = RAGCLI()
    
    try:
        if not await cli.initialize():
            return
        
        # Execute command
        if args.command == "test":
            await cli.test_connection()
        
        elif args.command == "list":
            await cli.list_stories()
        
        elif args.command == "index":
            if not args.prompt_file or not args.output_dir:
                print("index command requires --prompt-file and --output-dir")
                return
            await cli.index_story(args.prompt_file, args.output_dir)
        
        elif args.command == "search":
            if not args.prompt_file or not args.query:
                print("search command requires --prompt-file and --query")
                return
            await cli.search_content(args.prompt_file, args.query, args.content_type)
        
        elif args.command == "context":
            if not args.prompt_file or not args.chapter:
                print("context command requires --prompt-file and --chapter")
                return
            await cli.get_context(args.prompt_file, args.chapter, args.scene)
        
        elif args.command == "summary":
            if not args.prompt_file:
                print("summary command requires --prompt-file")
                return
            await cli.get_story_summary(args.prompt_file)
    
    finally:
        await cli.close()


if __name__ == "__main__":
    asyncio.run(main())
