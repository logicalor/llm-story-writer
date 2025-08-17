---
# AI Story Writer Configuration
# All configuration options are defined here in YAML frontmatter

# Model Configuration
models:
  initial_outline_writer: "ollama://huihui_ai/magistral-abliterated:24b?think=true"
  chapter_outline_writer: "ollama://huihui_ai/magistral-abliterated:24b?think=true"
  chapter_stage1_writer: "ollama://huihui_ai/magistral-abliterated:24b?think=true"
  chapter_stage2_writer: "ollama://huihui_ai/magistral-abliterated:24b?think=true"
  chapter_stage3_writer: "ollama://huihui_ai/magistral-abliterated:24b?think=true"
  chapter_stage4_writer: "ollama://huihui_ai/magistral-abliterated:24b?think=true"
  chapter_revision_writer: "ollama://huihui_ai/magistral-abliterated:24b?think=true"
  revision_model: "ollama://huihui_ai/magistral-abliterated:24b?think=true"
  eval_model: "ollama://huihui_ai/magistral-abliterated:24b?think=true"
  info_model: "ollama://huihui_ai/magistral-abliterated:24b?think=true"
  scrub_model: "ollama://huihui_ai/magistral-abliterated:24b?think=true"
  checker_model: "ollama://huihui_ai/magistral-abliterated:24b?think=true"
  translator_model: "ollama://huihui_ai/magistral-abliterated:24b?think=true"
  sanity_model: "ollama://huihui_ai/deepseek-r1-abliterated:7b?think=true"
  logical_model: "ollama://huihui_ai/qwen2.5-coder-abliterate:7b"
  scene_writer: "ollama://huihui_ai/magistral-abliterated:24b?think=true"
  creative_model: "ollama://huihui_ai/magistral-abliterated:24b?think=true"
  #scene_writer: "ollama://hf.co/DavidAU/L3-DARKEST-PLANET-16.5B-GGUF"

# Generation Settings
generation:
  seed: 12
  outline_quality: 87
  chapter_quality: 85
  wanted_chapters: 25
  outline_min_revisions: 0
  outline_max_revisions: 3
  chapter_min_revisions: 0
  chapter_max_revisions: 3
  enable_final_edit: false
  enable_scrubbing: true
  enable_chapter_revisions: true
  expand_outline: true
  scene_generation_pipeline: true
  enable_outline_critique: false
  outline_critique_iterations: 3
  stream: true
  debug: true
#  strategy: "outline-chapter"
  strategy: "outline-chapter"
  use_improved_recap_sanitizer: true
  use_multi_stage_recap_sanitizer: true
  use_chunked_outline_generation: true
  outline_chunk_size: 10
  log_prompt_inputs: true

# Translation Settings
translation:
  translate_language: null
  translate_prompt_language: null

# Infrastructure Settings
infrastructure:
  output_dir: "/home/shaun/Documents/stories/output"
  savepoint_dir: "/home/shaun/Documents/stories/saves"
  logs_dir: "Logs"
  ollama_host: "127.0.0.1:11434"
  llama_cpp_host: "127.0.0.1:8080"
  context_length: 16384
  randomize_seed: true
  
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

# API Keys (set via environment variables)
api_keys:
  google_api_key: null
  openrouter_api_key: null
---

# AI Story Writer Configuration Guide

This document contains all configuration options for the AI Story Writer application. The configuration is defined in the YAML frontmatter at the top of this file.

## 📋 Quick Start

### Basic Usage
```bash
python src/main.py Prompts/YourPrompt.txt
```

The application will use all the configuration options defined in the frontmatter above.

## 🎯 Configuration Options

All configuration options are defined in the YAML frontmatter at the top of this file. You can modify these values to customize the behavior of the application.

### Model Configuration

The `models` section defines which models to use for different parts of the story generation process:

- `initial_outline_writer`: Model for writing the base outline content
- `chapter_outline_writer`: Model for writing per-chapter outline content
- `chapter_stage1_writer`: Model for chapter stage 1 (plot)
- `chapter_stage2_writer`: Model for chapter stage 2 (character development)
- `chapter_stage3_writer`: Model for chapter stage 3 (dialogue)
- `chapter_stage4_writer`: Model for chapter stage 4 (final correction)
- `chapter_revision_writer`: Model for revising chapters
- `revision_model`: Model for generating constructive criticism
- `eval_model`: Model for evaluating story quality (0-100)
- `info_model`: Model for generating story summary/info
- `scrub_model`: Model for scrubbing story content
- `checker_model`: Model for checking if LLM cheated
- `translator_model`: Model for translating stories
- `sanity_model`: Model for sanity checks
- `logical_model`: Model for logical operations

### Generation Settings

The `generation` section controls the story generation process:

- `seed`: Random seed for model generation
- `outline_quality`: Target quality for outline generation
- `chapter_quality`: Target quality for chapter generation
- `outline_min_revisions`: Minimum number of outline revisions
- `outline_max_revisions`: Maximum number of outline revisions
- `chapter_min_revisions`: Minimum number of chapter revisions
- `chapter_max_revisions`: Maximum number of chapter revisions
- `enable_final_edit`: Enable final edit pass of entire story
- `enable_scrubbing`: Enable content scrubbing
- `enable_chapter_revisions`: Enable chapter revisions
- `expand_outline`: Enable chapter-by-chapter outline expansion
- `scene_generation_pipeline`: Use scene-by-scene generation pipeline
- `enable_outline_critique`: Enable iterative outline critique and refinement
- `outline_critique_iterations`: Maximum number of critique refinement iterations (1-10)
- `stream`: Enable real-time streaming of model output to console
- `debug`: Enable debug logging and verbose output
- `log_prompt_inputs`: Log full prompt inputs to console for debugging (shows exact prompts sent to models)
- `use_chunked_outline_generation`: Use chunked approach for initial outline generation (prevents skipping chapters with long outlines)
- `outline_chunk_size`: Number of chapters to generate per chunk when using chunked outline generation

### Translation Settings

The `translation` section controls translation features:

- `translate_language`: Language to translate the story to
- `translate_prompt_language`: Language to translate the input prompt to

### Infrastructure Settings

The `infrastructure` section controls system behavior:

- `output_dir`: Directory for output files
- `savepoint_dir`: Directory for savepoint files
- `logs_dir`: Directory for log files
- `ollama_host`: Ollama server host and port

#### RAG Configuration

The RAG (Retrieval-Augmented Generation) system configuration:

- `postgres_host`: PostgreSQL server host and port
- `postgres_database`: Database name for story data
- `postgres_user`: Database username
- `postgres_password`: Database password
- `embedding_model`: Model for generating text embeddings (see format below)
- `vector_dimensions`: Dimension of the embedding vectors (varies by model)
- `similarity_threshold`: Minimum similarity score for relevant content retrieval
- `max_context_chunks`: Maximum number of content chunks to retrieve for context
- `max_chunk_size`: Maximum size of content chunks in characters
- `overlap_size`: Overlap size between chunks in characters

## 🔧 Model Format Reference

### Ollama Models (Local)
```yaml
models:
  initial_outline_writer: "ollama://llama3:70b"
  chapter_stage1_writer: "ollama://llama3:70b@192.168.1.100:11434"
  info_model: "ollama://llama3:70b?temperature=0.7"
```

### Embedding Models (RAG System)
```yaml
infrastructure:
  # Ollama embedding models
  embedding_model: "ollama://nomic-embed-text"           # 1536 dimensions
  embedding_model: "ollama://all-MiniLM-L6-v2"          # 384 dimensions
  embedding_model: "ollama://text-embedding-3-small"    # 1536 dimensions
  
  # With custom host
  embedding_model: "ollama://nomic-embed-text@192.168.1.100:11434"
  
  # Vector dimensions must match the model
  vector_dimensions: 1536  # for nomic-embed-text
  vector_dimensions: 384   # for all-MiniLM-L6-v2
```

### Google Models (Cloud)
```yaml
models:
  initial_outline_writer: "google://gemini-1.5-pro"
  info_model: "google://gemini-1.5-flash"
```

### OpenRouter Models (Cloud)
```yaml
models:
  initial_outline_writer: "openrouter://anthropic/claude-3-opus"
  info_model: "openrouter://openai/gpt-4"
```

## 📝 Configuration Examples

### High-Quality Generation
```yaml
generation:
  outline_min_revisions: 2
  outline_max_revisions: 5
  chapter_min_revisions: 1
  chapter_max_revisions: 3
  enable_final_edit: true
  enable_outline_critique: true
  outline_critique_iterations: 5
```

### Fast Prototyping
```yaml
generation:
  outline_min_revisions: 0
  outline_max_revisions: 1
  chapter_min_revisions: 0
  chapter_max_revisions: 1
  enable_scrubbing: false
  enable_chapter_revisions: false
  enable_outline_critique: false
```

### Creative Writing
```yaml
models:
  initial_outline_writer: "ollama://llama3:70b?temperature=0.8"
  chapter_stage1_writer: "ollama://llama3:70b?temperature=0.8"

generation:
  seed: 42
```

### Critique-Focused Generation
```yaml
generation:
  enable_outline_critique: true
  outline_critique_iterations: 5
  outline_min_revisions: 1
  outline_max_revisions: 3
```

### Translation Workflow
```yaml
translation:
  translate_prompt_language: "Spanish"
  translate_language: "French"
```

### RAG System Configuration
```yaml
infrastructure:
  # High-quality embeddings (slower, more accurate)
  embedding_model: "ollama://nomic-embed-text"
  vector_dimensions: 1536
  similarity_threshold: 0.8
  
  # Fast embeddings (faster, good quality)
  embedding_model: "ollama://all-MiniLM-L6-v2"
  vector_dimensions: 384
  similarity_threshold: 0.7
  
  # Balanced approach
  embedding_model: "ollama://text-embedding-3-small"
  vector_dimensions: 1536
  similarity_threshold: 0.75
```

### Changing Embedding Models

**⚠️ Important**: If you change the embedding model after indexing content, you'll need to migrate your data.

**Before indexing content** (recommended):
1. Set your desired `embedding_model` in config.md
2. Run `./setup_rag.sh` to set up with the new model

**After indexing content** (requires migration):
1. Update `embedding_model` in config.md
2. Run `./migrate_embed.sh fast` or `./migrate_embed.sh accurate`
3. The migration script will re-embed all content with the new model

**Migration commands**:
```bash
./migrate_embed.sh fast        # Switch to fast model (384d)
./migrate_embed.sh accurate    # Switch to accurate model (1536d)
./migrate_embed.sh dry-run     # See what would be migrated
```

### Chunked Outline Generation (for Long Stories)
```yaml
generation:
  wanted_chapters: 75  # Large number of chapters
  use_chunked_outline_generation: true  # Prevent chapter skipping
  outline_chunk_size: 4  # Generate 4 chapters per chunk
```

### Debugging and Development
```yaml
generation:
  debug: true  # Enable debug logging
  log_prompt_inputs: true  # Log full prompts sent to models
  stream: true  # Show real-time model output
```

## 🔍 Environment Variables

Create a `.env` file in the project root for API keys:

```bash
# .env
GOOGLE_API_KEY=your_google_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

## 📊 Performance Tips

### Faster Generation
- Set `outline_min_revisions: 0` and `chapter_min_revisions: 0`
- Set `enable_scrubbing: false` and `enable_chapter_revisions: false`
- Use smaller models for faster processing

### Higher Quality
- Use larger models (70B+ parameters)
- Set `enable_final_edit: true`
- Increase revision counts
- Use models with higher temperature for creativity

### Memory Optimization
- Use models that fit in your available RAM
- Consider using cloud models for large models
- Monitor system resources during generation

### Long Story Generation
- Use `use_chunked_outline_generation: true` for stories with 30+ chapters
- Adjust `outline_chunk_size` based on model capabilities (4-8 chapters work well)
- Chunked generation prevents chapter skipping due to token limits

### Debugging and Development
- Enable `log_prompt_inputs: true` to see exactly what prompts are sent to models
- Combine with `debug: true` for comprehensive debugging information
- **Warning**: Prompt logging generates very verbose output - disable for production runs

## 🐛 Troubleshooting

### Common Issues

1. **Model Not Found**: Ensure the model is available in your Ollama installation
   ```bash
   ollama list
   ollama pull llama3:70b
   ```

2. **API Key Errors**: Check your `.env` file for correct API keys
   ```bash
   cat .env
   ```

3. **Memory Issues**: Use smaller models or cloud providers
   ```yaml
   models:
     initial_outline_writer: "ollama://llama3:8b"
   ```

4. **Slow Generation**: Use faster configuration
   ```yaml
   generation:
     outline_min_revisions: 0
     chapter_min_revisions: 0
     enable_scrubbing: false
     enable_chapter_revisions: false
   ```

### Streaming Output
Enable real-time streaming of model output:
```yaml
generation:
  stream: true
```

### Debug Mode
Enable debug mode for detailed logging:
```yaml
generation:
  debug: true
```

## 📚 Additional Resources

- [README.md](README.md) - Main project documentation
- [REFACTORING_COMPLETION_SUMMARY.md](REFACTORING_COMPLETION_SUMMARY.md) - Architecture overview 