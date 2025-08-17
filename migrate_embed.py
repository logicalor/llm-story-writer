#!/usr/bin/env python3
"""
Embedding Model Migration Script for AI Story Writer RAG System

This script allows you to migrate from one embedding model to another while preserving
all your indexed content. It will:

1. Detect the current and new embedding model dimensions
2. Create a new table with the correct vector dimensions
3. Re-embed all existing content using the new model
4. Swap the tables and clean up

Usage:
    python migrate_embed.py --new-model "ollama://all-MiniLM-L6-v2"
    python migrate_embed.py --new-model "ollama://nomic-embed-text" --dry-run
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config.rag_config import RAGConfigLoader, RAGConfig
from infrastructure.providers.ollama_embedding_provider import OllamaEmbeddingProvider
from infrastructure.storage.pgvector_store import PgVectorStore
from application.services.rag_service import RAGService


class EmbeddingMigrator:
    """Handles migration between different embedding models."""
    
    def __init__(self, config: RAGConfig):
        self.config = config
        self.old_vector_store: Optional[PgVectorStore] = None
        self.new_vector_store: Optional[PgVectorStore] = None
        self.embedding_provider: Optional[OllamaEmbeddingProvider] = None
        
    async def initialize(self):
        """Initialize the migration components."""
        try:
            # Create embedding provider with new model
            self.embedding_provider = OllamaEmbeddingProvider(
                host=self.config.ollama_host,
                model=self.config.embedding_model_name
            )
            
            # Test the new embedding model
            print(f"🧪 Testing new embedding model: {self.config.embedding_model_name}")
            if not await self.embedding_provider.test_connection():
                raise Exception("Failed to connect to Ollama")
            
            # Test embedding generation
            test_embedding = await self.embedding_provider.get_single_embedding("test")
            actual_dimensions = len(test_embedding)
            expected_dimensions = self.config.vector_dimensions
            
            if actual_dimensions != expected_dimensions:
                print(f"⚠️  Warning: Model generates {actual_dimensions} dimensions, config expects {expected_dimensions}")
                print(f"   Updating config to use actual dimensions: {actual_dimensions}")
                self.config.vector_dimensions = actual_dimensions
            
            print(f"✅ New embedding model ready: {actual_dimensions} dimensions")
            
        except Exception as e:
            print(f"❌ Failed to initialize new embedding model: {e}")
            raise
    
    async def analyze_migration(self) -> Dict[str, Any]:
        """Analyze what needs to be migrated."""
        print("🔍 Analyzing migration requirements...")
        
        # Connect to existing database
        old_config = RAGConfig(
            postgres_host=self.config.postgres_host,
            postgres_database=self.config.postgres_database,
            postgres_user=self.config.postgres_user,
            postgres_password=self.config.postgres_password,
            embedding_model="ollama://legacy-model",  # Placeholder
            vector_dimensions=1536,  # Assume legacy dimensions
            similarity_threshold=self.config.similarity_threshold,
            max_context_chunks=self.config.max_context_chunks
        )
        
        self.old_vector_store = PgVectorStore(old_config.connection_string)
        await self.old_vector_store.initialize()
        
        # Get current database info
        stories = await self.old_vector_store.list_stories()
        total_chunks = 0
        content_summary = {}
        
        for story in stories:
            story_id = story['id']
            chunks = await self.old_vector_store.get_story_content(story_id)
            total_chunks += len(chunks)
            
            # Count by content type
            for _, content_type, _, _ in chunks:
                content_summary[content_type] = content_summary.get(content_type, 0) + 1
        
        # Determine current vector dimensions by querying the database schema
        current_dimensions = 1536  # Default fallback
        try:
            async with self.old_vector_store._pool.acquire() as conn:
                # Use a simpler approach: check if the table exists and has content
                table_exists = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'content_chunks'
                    )
                """)
                
                if table_exists:
                    # Check if there are any chunks with embeddings
                    chunk_count = await conn.fetchval("SELECT COUNT(*) FROM content_chunks WHERE embedding IS NOT NULL")
                    
                    if chunk_count > 0:
                        # Get the actual vector dimensions from the column definition
                        result = await conn.fetchval("""
                            SELECT atttypmod 
                            FROM pg_attribute 
                            JOIN pg_class ON pg_attribute.attrelid = pg_class.oid 
                            WHERE pg_class.relname = 'content_chunks' 
                            AND pg_attribute.attname = 'embedding'
                        """)
                        
                        if result and result > 0:
                            current_dimensions = result
                            print(f"   🔍 Detected current vector dimensions: {current_dimensions}")
                        else:
                            print(f"   ⚠️  Could not detect vector dimensions, using default: {current_dimensions}")
                    else:
                        print(f"   📝 No existing embeddings found, using default: {current_dimensions}")
                else:
                    print(f"   📝 No content_chunks table found, using default: {current_dimensions}")
        except Exception as e:
            print(f"   ⚠️  Error detecting vector dimensions: {e}, using default: {current_dimensions}")
        
        migration_info = {
            "current_dimensions": current_dimensions,
            "new_dimensions": self.config.vector_dimensions,
            "stories_count": len(stories),
            "total_chunks": total_chunks,
            "content_summary": content_summary,
            "needs_migration": current_dimensions != self.config.vector_dimensions
        }
        
        print(f"📊 Migration Analysis:")
        print(f"   Current vector dimensions: {current_dimensions}")
        print(f"   New vector dimensions: {self.config.vector_dimensions}")
        print(f"   Stories to migrate: {len(stories)}")
        print(f"   Content chunks to migrate: {total_chunks}")
        print(f"   Content types: {', '.join(f'{k}: {v}' for k, v in content_summary.items())}")
        
        if migration_info["needs_migration"]:
            print(f"   🔄 Migration required: dimension mismatch")
        else:
            print(f"   ✅ No migration needed: dimensions match")
        
        return migration_info
    
    async def create_migration_table(self) -> str:
        """Create a new table with the correct vector dimensions."""
        print("🏗️  Creating migration table...")
        
        # Create new vector store with new dimensions
        new_config = RAGConfig(
            postgres_host=self.config.postgres_host,
            postgres_database=self.config.postgres_database,
            postgres_user=self.config.postgres_user,
            postgres_password=self.config.postgres_password,
            embedding_model=self.config.embedding_model,
            vector_dimensions=self.config.vector_dimensions,
            similarity_threshold=self.config.similarity_threshold,
            max_context_chunks=self.config.max_context_chunks
        )
        
        self.new_vector_store = PgVectorStore(new_config.connection_string)
        await self.new_vector_store.initialize()
        
        # Create migration table
        migration_table_name = f"content_chunks_migration_{self.config.vector_dimensions}"
        
        async with self.new_vector_store._pool.acquire() as conn:
            # Drop existing migration table if it exists (with better error handling)
            try:
                await conn.execute(f"DROP TABLE IF EXISTS {migration_table_name} CASCADE")
            except Exception as e:
                print(f"⚠️  Warning: Could not drop existing migration table: {e}")
                # Try to force drop any remaining indexes
                await conn.execute(f"""
                    DO $$ 
                    BEGIN
                        DROP INDEX IF EXISTS idx_{migration_table_name}_story_id CASCADE;
                        DROP INDEX IF EXISTS idx_{migration_table_name}_content_type CASCADE;
                        DROP INDEX IF EXISTS idx_{migration_table_name}_chapter_scene CASCADE;
                        DROP INDEX IF EXISTS idx_{migration_table_name}_created_at CASCADE;
                        DROP INDEX IF EXISTS idx_{migration_table_name}_metadata_gin CASCADE;
                        DROP INDEX IF EXISTS idx_{migration_table_name}_content_type_subtype CASCADE;
                        DROP INDEX IF EXISTS idx_{migration_table_name}_embedding_hnsw CASCADE;
                        DROP INDEX IF EXISTS idx_{migration_table_name}_embedding_ivfflat CASCADE;
                    EXCEPTION
                        WHEN OTHERS THEN NULL;
                    END $$;
                """)
                # Try dropping the table again
                await conn.execute(f"DROP TABLE IF EXISTS {migration_table_name} CASCADE")
            
            # Create the migration table
            await conn.execute(f"""
                CREATE TABLE {migration_table_name} (
                    id SERIAL PRIMARY KEY,
                    story_id INTEGER REFERENCES stories(id) ON DELETE CASCADE,
                    content_type VARCHAR(50) NOT NULL,
                    content_subtype VARCHAR(50),
                    title VARCHAR(255),
                    content TEXT NOT NULL,
                    metadata JSONB,
                    embedding vector({self.config.vector_dimensions}),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    chapter_number INTEGER,
                    scene_number INTEGER
                )
            """)
            
            # Create indexes
            await conn.execute(f"CREATE INDEX idx_{migration_table_name}_story_id ON {migration_table_name}(story_id)")
            await conn.execute(f"CREATE INDEX idx_{migration_table_name}_content_type ON {migration_table_name}(content_type)")
            await conn.execute(f"CREATE INDEX idx_{migration_table_name}_chapter_scene ON {migration_table_name}(chapter_number, scene_number)")
            await conn.execute(f"CREATE INDEX idx_{migration_table_name}_created_at ON {migration_table_name}(created_at)")
            await conn.execute(f"CREATE INDEX idx_{migration_table_name}_metadata_gin ON {migration_table_name} USING GIN (metadata)")
            await conn.execute(f"CREATE INDEX idx_{migration_table_name}_content_type_subtype ON {migration_table_name}(content_type, content_subtype)")
            
            # Create vector indexes
            await conn.execute(f"CREATE INDEX idx_{migration_table_name}_embedding_hnsw ON {migration_table_name} USING hnsw (embedding vector_cosine_ops)")
            await conn.execute(f"CREATE INDEX idx_{migration_table_name}_embedding_ivfflat ON {migration_table_name} USING ivfflat (embedding vector_cosine_ops)")
        
        print(f"✅ Created migration table: {migration_table_name}")
        return migration_table_name
    
    async def migrate_content(self, migration_table_name: str, dry_run: bool = False) -> Dict[str, Any]:
        """Migrate content from old table to new table with new embeddings."""
        print("🔄 Starting content migration...")
        
        if dry_run:
            print("🧪 DRY RUN MODE - No actual changes will be made")
        
        # Get all stories
        stories = await self.old_vector_store.list_stories()
        migration_stats = {
            "stories_processed": 0,
            "chunks_migrated": 0,
            "errors": 0,
            "content_types": {}
        }
        
        for story in stories:
            story_id = story['id']
            print(f"📚 Processing story: {story['story_name']} (ID: {story_id})")
            
            # Get all content for this story
            chunks = await self.old_vector_store.get_story_content(story_id)
            
            for chunk_id, content_type, content, metadata in chunks:
                try:
                    if not dry_run:
                        # Generate new embedding with new model
                        new_embedding = await self.embedding_provider.get_single_embedding(content)
                        
                        # Insert into migration table
                        async with self.new_vector_store._pool.acquire() as conn:
                            await conn.execute(f"""
                                INSERT INTO {migration_table_name} 
                                (story_id, content_type, content_subtype, title, content, metadata, 
                                 embedding, chapter_number, scene_number)
                                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                            """, 
                                story_id, content_type, metadata.get('content_subtype'), 
                                metadata.get('title'), content, metadata,
                                new_embedding, metadata.get('chapter_number'), 
                                metadata.get('scene_number')
                            )
                    
                    migration_stats["chunks_migrated"] += 1
                    migration_stats["content_types"][content_type] = migration_stats["content_types"].get(content_type, 0) + 1
                    
                    if migration_stats["chunks_migrated"] % 10 == 0:
                        print(f"   ✅ Migrated {migration_stats['chunks_migrated']} chunks...")
                        
                except Exception as e:
                    print(f"   ❌ Error migrating chunk {chunk_id}: {e}")
                    migration_stats["errors"] += 1
            
            migration_stats["stories_processed"] += 1
        
        print(f"📊 Migration completed:")
        print(f"   Stories processed: {migration_stats['stories_processed']}")
        print(f"   Chunks migrated: {migration_stats['chunks_migrated']}")
        print(f"   Errors: {migration_stats['errors']}")
        print(f"   Content types: {', '.join(f'{k}: {v}' for k, v in migration_stats['content_types'].items())}")
        
        return migration_stats
    
    async def swap_tables(self, migration_table_name: str, dry_run: bool = False) -> bool:
        """Swap the old table with the new migration table."""
        print("🔄 Swapping tables...")
        
        if dry_run:
            print("🧪 DRY RUN MODE - No actual changes will be made")
            return True
        
        try:
            async with self.new_vector_store._pool.acquire() as conn:
                # Check if the old table has any content
                old_table_count = await conn.fetchval("SELECT COUNT(*) FROM content_chunks")
                
                if old_table_count == 0:
                    print("📝 Old table is empty, dropping and recreating...")
                    # Drop the old empty table
                    await conn.execute("DROP TABLE IF EXISTS content_chunks")
                    
                    # Rename migration table to main table
                    await conn.execute(f"ALTER TABLE {migration_table_name} RENAME TO content_chunks")
                    
                    # Recreate indexes with correct names
                    await conn.execute(f"ALTER INDEX idx_{migration_table_name}_story_id RENAME TO idx_content_chunks_story_id")
                    await conn.execute(f"ALTER INDEX idx_{migration_table_name}_content_type RENAME TO idx_content_chunks_content_type")
                    await conn.execute(f"ALTER INDEX idx_{migration_table_name}_chapter_scene RENAME TO idx_content_chunks_chapter_scene")
                    await conn.execute(f"ALTER INDEX idx_{migration_table_name}_created_at RENAME TO idx_content_chunks_created_at")
                    await conn.execute(f"ALTER INDEX idx_{migration_table_name}_metadata_gin RENAME TO idx_content_chunks_metadata_gin")
                    await conn.execute(f"ALTER INDEX idx_{migration_table_name}_content_type_subtype RENAME TO idx_content_chunks_content_type_subtype")
                    await conn.execute(f"ALTER INDEX idx_{migration_table_name}_embedding_hnsw RENAME TO idx_content_chunks_embedding_hnsw")
                    await conn.execute(f"ALTER INDEX idx_{migration_table_name}_embedding_ivfflat RENAME TO idx_content_chunks_embedding_ivfflat")
                else:
                    print(f"📝 Old table has {old_table_count} chunks, performing full swap...")
                    # Rename old table to backup
                    await conn.execute("ALTER TABLE content_chunks RENAME TO content_chunks_backup")
                    
                    # Rename migration table to main table
                    await conn.execute(f"ALTER TABLE {migration_table_name} RENAME TO content_chunks")
                    
                    # Recreate indexes with correct names
                    await conn.execute(f"ALTER INDEX idx_{migration_table_name}_story_id RENAME TO idx_content_chunks_story_id")
                    await conn.execute(f"ALTER INDEX idx_{migration_table_name}_content_type RENAME TO idx_content_chunks_content_type")
                    await conn.execute(f"ALTER INDEX idx_{migration_table_name}_chapter_scene RENAME TO idx_content_chunks_chapter_scene")
                    await conn.execute(f"ALTER INDEX idx_{migration_table_name}_created_at RENAME TO idx_content_chunks_created_at")
                    await conn.execute(f"ALTER INDEX idx_{migration_table_name}_metadata_gin RENAME TO idx_content_chunks_metadata_gin")
                    await conn.execute(f"ALTER INDEX idx_{migration_table_name}_content_type_subtype RENAME TO idx_content_chunks_content_type_subtype")
                    await conn.execute(f"ALTER INDEX idx_{migration_table_name}_embedding_hnsw RENAME TO idx_content_chunks_embedding_hnsw")
                    await conn.execute(f"ALTER INDEX idx_{migration_table_name}_embedding_ivfflat RENAME TO idx_content_chunks_embedding_ivfflat")
            
            print("✅ Tables swapped successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to swap tables: {e}")
            return False
    
    async def cleanup_backup(self, dry_run: bool = False) -> bool:
        """Clean up the backup table after successful migration."""
        print("🧹 Cleaning up backup table...")
        
        if dry_run:
            print("🧪 DRY RUN MODE - No actual changes will be made")
            return True
        
        try:
            async with self.new_vector_store._pool.acquire() as conn:
                await conn.execute("DROP TABLE IF EXISTS content_chunks_backup")
            
            print("✅ Backup table cleaned up")
            return True
            
        except Exception as e:
            print(f"❌ Failed to cleanup backup: {e}")
            return False
    
    async def record_migration_start(self, migration_info: Dict[str, Any]) -> None:
        """Record the start of a migration."""
        try:
            if self.new_vector_store and self.new_vector_store._pool:
                async with self.new_vector_store._pool.acquire() as conn:
                    result = await conn.execute("""
                        INSERT INTO migration_status 
                        (migration_type, from_dimensions, to_dimensions, status, migration_table_name)
                        VALUES ($1, $2, $3, $4, $5)
                        RETURNING id
                    """, 
                        "embedding_model_change",
                        migration_info.get("current_dimensions"),
                        migration_info.get("new_dimensions"),
                        "in_progress",
                        f"content_chunks_migration_{self.config.vector_dimensions}"
                    )
                    print(f"   📝 Migration status recorded (ID: {result})")
            else:
                print(f"   ⚠️  Warning: No vector store pool available for status recording")
        except Exception as e:
            print(f"   ⚠️  Warning: Could not record migration start: {e}")
            import traceback
            traceback.print_exc()
    
    async def record_migration_completion(self, success: bool, error_message: str = None) -> None:
        """Record the completion of a migration."""
        try:
            if self.new_vector_store and self.new_vector_store._pool:
                async with self.new_vector_store._pool.acquire() as conn:
                    status = "completed" if success else "failed"
                    result = await conn.execute("""
                        UPDATE migration_status 
                        SET status = $1, completed_at = CURRENT_TIMESTAMP, error_message = $2
                        WHERE id = (
                            SELECT id FROM migration_status 
                            WHERE status = 'in_progress' 
                            ORDER BY created_at DESC 
                            LIMIT 1
                        )
                    """, status, error_message)
                    print(f"   📝 Migration completion recorded: {status}")
            else:
                print(f"   ⚠️  Warning: No vector store pool available for completion recording")
        except Exception as e:
            print(f"   ⚠️  Warning: Could not record migration completion: {e}")
            import traceback
            traceback.print_exc()
    
    async def cleanup_migration_tables(self) -> bool:
        """Clean up any leftover migration tables."""
        print("🧹 Cleaning up leftover migration tables...")
        
        try:
            async with self.new_vector_store._pool.acquire() as conn:
                # Find all migration tables
                migration_tables = await conn.fetch("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name LIKE 'content_chunks_migration_%'
                """)
                
                if migration_tables:
                    for table in migration_tables:
                        table_name = table['table_name']
                        await conn.execute(f"DROP TABLE {table_name} CASCADE")
                        print(f"   🗑️  Dropped {table_name}")
                    print("✅ Migration tables cleaned up")
                else:
                    print("📝 No migration tables found to clean up")
            
            return True
            
        except Exception as e:
            print(f"⚠️  Warning: Could not cleanup migration tables: {e}")
            return False
    
    async def close(self):
        """Close all connections."""
        if self.old_vector_store:
            await self.old_vector_store.close()
        if self.new_vector_store:
            await self.new_vector_store.close()


async def main():
    """Main migration function."""
    parser = argparse.ArgumentParser(description="Migrate embedding models in RAG system")
    parser.add_argument("--new-model", required=True, help="New embedding model (e.g., ollama://all-MiniLM-L6-v2)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--skip-cleanup", action="store_true", help="Skip cleanup of backup table")
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Load configuration
        from config.config_loader import ConfigLoader
        base_config_loader = ConfigLoader()
        config_loader = RAGConfigLoader(base_config_loader)
        config = config_loader.load_rag_config()
        
        # Update config with new model
        config.embedding_model = args.new_model
        
        # Validate new configuration
        errors = config_loader.validate_config(config)
        if errors:
            print("❌ Configuration errors:")
            for error in errors:
                print(f"   - {error}")
            return 1
        
        print(f"🚀 Starting embedding model migration...")
        print(f"   New model: {args.new_model}")
        print(f"   New dimensions: {config.vector_dimensions}")
        
        # Initialize migrator
        migrator = EmbeddingMigrator(config)
        await migrator.initialize()
        
        # Analyze migration
        migration_info = await migrator.analyze_migration()
        
        if not migration_info["needs_migration"]:
            print("✅ No migration needed - dimensions already match")
            return 0
        
        # Confirm migration
        if not args.dry_run:
            response = input(f"\n⚠️  This will migrate {migration_info['total_chunks']} content chunks. Continue? (y/N): ")
            if response.lower() != 'y':
                print("❌ Migration cancelled")
                return 1
        
        # Create migration table
        migration_table = await migrator.create_migration_table()
        
        # Record migration start (after vector store is initialized)
        await migrator.record_migration_start(migration_info)
        
        # Migrate content
        migration_stats = await migrator.migrate_content(migration_table, args.dry_run)
        
        if migration_stats["errors"] > 0 and not args.dry_run:
            print(f"⚠️  Migration completed with {migration_stats['errors']} errors")
            response = input("Continue with table swap? (y/N): ")
            if response.lower() != 'y':
                print("❌ Migration cancelled - backup table preserved")
                return 1
        
        # Swap tables
        if not await migrator.swap_tables(migration_table, args.dry_run):
            print("❌ Failed to swap tables - backup preserved")
            return 1
        
        # Cleanup
        if not args.skip_cleanup:
            await migrator.cleanup_backup(args.dry_run)
        
        # Record successful migration completion
        await migrator.record_migration_completion(True)
        
        # Final cleanup: remove any leftover migration tables
        try:
            await migrator.cleanup_migration_tables()
        except Exception as e:
            print(f"⚠️  Warning: Could not cleanup migration tables: {e}")
        
        print("🎉 Migration completed successfully!")
        print(f"   New embedding model: {config.embedding_model_name}")
        print(f"   New vector dimensions: {config.vector_dimensions}")
        
        return 0
        
    except Exception as e:
        # Record failed migration
        if 'migrator' in locals():
            await migrator.record_migration_completion(False, str(e))
        
        print(f"❌ Migration failed: {e}")
        return 1
    
    finally:
        if 'migrator' in locals():
            await migrator.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
