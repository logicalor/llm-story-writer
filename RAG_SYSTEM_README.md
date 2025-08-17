# RAG System for AI Story Writer

This document describes the RAG (Retrieval-Augmented Generation) system integrated with AI Story Writer, which provides intelligent content indexing, search, and context retrieval for story generation.

## 🏗️ Architecture Overview

The RAG system consists of several key components:

- **PostgreSQL + pgvector**: Vector database for storing embeddings and content
- **Ollama Embedding Provider**: Local embedding generation using Ollama models
- **Content Chunker**: Intelligent text chunking for optimal embedding
- **RAG Service**: Core service for content indexing and retrieval
- **RAG Integration Service**: Integration with the story generation pipeline

## 🚀 Quick Start

### 1. Prerequisites

- Docker and Docker Compose
- Ollama running locally
- Python 3.8+

### 2. Setup

Run the automated setup script:

```bash
./setup_rag.sh
```

This script will:
- Pull the `nomic-embed-text` embedding model
- Start PostgreSQL with pgvector
- Install Python dependencies
- Verify the setup

### 3. Test the System

```bash
# Test connections
python src/presentation/cli/rag_cli.py test

# List stories (should be empty initially)
python src/presentation/cli/rag_cli.py list
```

## 📚 Usage

### CLI Commands

The RAG system provides a comprehensive CLI for management:

```bash
# Test connections
python src/presentation/cli/rag_cli.py test

# List all stories
python src/presentation/cli/rag_cli.py list

# Index an existing story
python src/presentation/cli/rag_cli.py index \
  --prompt-file Prompts/YourPrompt.txt \
  --output-dir Stories/YourStory

# Search for content
python src/presentation/cli/rag_cli.py search \
  --prompt-file Prompts/YourPrompt.txt \
  --query "character motivation"

# Get generation context
python src/presentation/cli/rag_cli.py context \
  --prompt-file Prompts/YourPrompt.txt \
  --chapter 5

# Get story summary
python src/presentation/cli/rag_cli.py summary \
  --prompt-file Prompts/YourPrompt.txt
```

### Content Types

The system indexes several types of content:

- **`outline`**: Story outlines and chapter summaries
- **`scene`**: Chapter and scene content
- **`character`**: Character sheets and development
- **`setting`**: Location and world descriptions
- **`event`**: Plot events and recaps

### Content Chunking

Content is automatically chunked for optimal embedding:

- **Semantic chunking**: Splits by logical boundaries (paragraphs, scenes)
- **Configurable size**: Default max chunk size of 1000 characters
- **Overlap**: 200 character overlap between chunks for context
- **Intelligent splitting**: Handles different content types appropriately

## 🔧 Configuration

### RAG Configuration

Add these settings to your `config.md`:

```yaml
infrastructure:
  # ... existing config ...
  
  # RAG Configuration
  postgres_host: "localhost:5432"
  postgres_database: "story_writer"
  postgres_user: "story_user"
  postgres_password: "story_pass"
  embedding_model: "ollama://nomic-embed-text"
  vector_dimensions: 1536
  similarity_threshold: 0.7
  max_context_chunks: 20
  max_chunk_size: 1000
  overlap_size: 200
```

### Environment Variables

Create a `.env` file for sensitive configuration:

```bash
# .env
POSTGRES_PASSWORD=your_secure_password
```

## 🗄️ Database Schema

### Stories Table

```sql
CREATE TABLE stories (
    id SERIAL PRIMARY KEY,
    story_name VARCHAR(255) UNIQUE NOT NULL,
    prompt_file_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Content Chunks Table

```sql
CREATE TABLE content_chunks (
    id SERIAL PRIMARY KEY,
    story_id INTEGER REFERENCES stories(id) ON DELETE CASCADE,
    content_type VARCHAR(50) NOT NULL,
    content_subtype VARCHAR(50),
    title VARCHAR(255),
    content TEXT NOT NULL,
    metadata JSONB,
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    chapter_number INTEGER,
    scene_number INTEGER
);
```

### Indexes

- **HNSW Index**: Fast approximate similarity search
- **IVFFlat Index**: Accurate similarity search
- **Content Type Index**: Filter by content type
- **Chapter/Scene Index**: Filter by story position

## 🔍 Search and Retrieval

### Similarity Search

```python
# Search for similar content
results = await rag_service.search_similar(
    story_id=story_id,
    query="character development",
    content_type="character",
    limit=10
)
```

### Context Retrieval

```python
# Get context for story generation
context = await rag_service.get_context_for_generation(
    story_id=story_id,
    chapter_number=5,
    scene_number=1
)
```

### Content Filtering

```python
# Get specific content types
character_chunks = await vector_store.get_story_content(
    story_id=story_id,
    content_type="character"
)
```

## 🔄 Integration with Story Generation

### Automatic Indexing

The RAG system automatically indexes content as it's generated:

```python
# In your story generation pipeline
await rag_integration.index_chapter(
    prompt_file_path=prompt_path,
    chapter_content=chapter_text,
    chapter_number=chapter_num
)
```

### Context-Aware Generation

Retrieve relevant context during generation:

```python
# Get context for the current chapter
context = await rag_integration.get_generation_context(
    prompt_file_path=prompt_path,
    chapter_number=current_chapter
)

# Use context in your generation prompts
enhanced_prompt = f"{base_prompt}\n\nContext:\n{context}"
```

## 📊 Performance and Optimization

### Indexing Strategy

- **HNSW**: Fast approximate search (recommended for real-time)
- **IVFFlat**: Accurate search (recommended for analysis)
- **Hybrid approach**: Use both based on use case

### Chunking Strategy

- **Semantic boundaries**: Preserve context across chunks
- **Configurable overlap**: Maintain continuity
- **Size optimization**: Balance chunk size vs. embedding quality

### Caching

- **Connection pooling**: Efficient database connections
- **Story ID caching**: Avoid repeated database lookups
- **Embedding caching**: Store computed embeddings

## 🔄 Embedding Model Migration

### Changing Embedding Models

If you want to change your embedding model after setting up the RAG system, use the migration script:

```bash
# Quick migration to fast model (384 dimensions)
./migrate_embed.sh fast

# Quick migration to accurate model (1536 dimensions)
./migrate_embed.sh accurate

# Custom model migration
./migrate_embed.sh custom ollama://bge-large-en

# Dry run to see what would be migrated
./migrate_embed.sh dry-run

# Analyze current database state
./migrate_embed.sh analyze
```

### Migration Process

The migration script will:

1. **Analyze** your current database and content
2. **Create** a new table with the correct vector dimensions
3. **Re-embed** all content using the new model
4. **Swap** the tables atomically
5. **Clean up** the old table

### Migration Safety Features

- **Dry-run mode**: Test migration without making changes
- **Backup preservation**: Old table is preserved until cleanup
- **Error handling**: Migration stops if errors occur
- **Rollback capability**: Can restore from backup if needed

### Supported Models

- **Fast models**: `all-MiniLM-L6-v2` (384d), `bge-small-en` (384d)
- **Balanced models**: `text-embedding-3-small` (1536d), `bge-base-en` (768d)
- **High-quality models**: `nomic-embed-text` (1536d), `bge-large-en` (1024d)

## 🐛 Troubleshooting

### Common Issues

1. **PostgreSQL Connection Failed**
   ```bash
   # Check if container is running
   docker-compose ps
   
   # Check logs
   docker-compose logs postgres
   ```

2. **Ollama Connection Failed**
   ```bash
   # Check if Ollama is running
   curl http://127.0.0.1:11434/api/tags
   
   # Check Ollama logs
   ollama logs
   ```

3. **Embedding Model Not Found**
   ```bash
   # Pull the required model
   ollama pull nomic-embed-text
   
   # List available models
   ollama list
   ```

4. **Vector Extension Error**
   ```bash
   # Recreate the container
   docker-compose down
   docker-compose up -d postgres
   ```

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🔮 Future Enhancements

### Planned Features

- **Hybrid Search**: Combine vector and keyword search
- **Content Summarization**: Automatic content summarization
- **Advanced Analytics**: Story structure analysis
- **Multi-language Support**: Internationalization
- **Real-time Updates**: Live content indexing

### Extensibility

The system is designed for easy extension:

- **Custom Content Types**: Add new content types easily
- **Custom Chunking**: Implement specialized chunking strategies
- **Custom Embeddings**: Support different embedding models
- **Custom Storage**: Support other vector databases

## 📚 API Reference

### RAGService

Core service for content management:

```python
class RAGService:
    async def index_content(self, story_id, content_type, content, ...)
    async def search_similar(self, story_id, query, ...)
    async def get_context_for_generation(self, story_id, chapter_number, ...)
    async def get_story_summary(self, story_id)
```

### RAGIntegrationService

Integration with story generation:

```python
class RAGIntegrationService:
    async def index_chapter(self, prompt_file_path, chapter_content, ...)
    async def index_character(self, prompt_file_path, character_content, ...)
    async def get_generation_context(self, prompt_file_path, chapter_number, ...)
```

### ContentChunker

Intelligent content chunking:

```python
class ContentChunker:
    def chunk_text(self, text, chunk_type, ...)
    def chunk_chapter(self, chapter_content, chapter_number, ...)
    def chunk_character_sheet(self, character_content, character_name, ...)
```

## 🤝 Contributing

To contribute to the RAG system:

1. Follow the existing code style
2. Add tests for new functionality
3. Update documentation
4. Ensure backward compatibility

## 📄 License

This RAG system is part of AI Story Writer and follows the same license terms.

## 🆘 Support

For issues and questions:

1. Check the troubleshooting section
2. Review the logs for error details
3. Test with the CLI tools
4. Check the configuration settings

---

**Happy Story Writing with AI and RAG! 🚀📚**
