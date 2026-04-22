# AI Story Writer Configuration Guide

This document describes all configuration options for the AI Story Writer application. The active configuration lives in `config.yml`.

## 📋 Quick Start

### Basic Usage
```bash
opencode
```

Then run `/new-story prompts/YourPrompt.txt` inside OpenCode. The application will use all the configuration options defined in `config.yml`.

## 🎯 Configuration Options

All configuration options are defined in `config.yml`. You can modify these values to customize the behavior of the application.

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
- `model_api_base`: Base URL for the OpenAI-compatible model API

Backward compatibility:

- `ollama_host` is still accepted and normalized to `model_api_base`
- `ollama://` model URIs are still accepted and map to the OpenAI-compatible provider
- `?think=true` is stripped from model URIs; for reasoning models such as DeepSeek-R1 and Qwen3, thinking mode is now controlled server-side (for example via Ollama model defaults)

#### RAG Configuration

The RAG (Retrieval-Augmented Generation) system uses ChromaDB-backed wiki retrieval:

- `embedding_model`: Model for generating text embeddings (see format below)
- `vector_dimensions`: Dimension of the embedding vectors (varies by model)
- `similarity_threshold`: Minimum similarity score for relevant content retrieval
- `max_context_chunks`: Maximum number of content chunks to retrieve for context
- `max_chunk_size`: Maximum size of content chunks in characters
- `overlap_size`: Overlap size between chunks in characters

## 🔧 Model Format Reference

### OpenAI-Compatible Models (Local)
```yaml
models:
  initial_outline_writer: "openai-compat://llama3:70b"
  chapter_stage1_writer: "openai-compat://llama3:70b@192.168.1.100:11434"
  info_model: "openai-compat://llama3:70b?temperature=0.7"
```

For reasoning models such as DeepSeek-R1 and Qwen3, do not rely on `?think=true` in the URI. The provider strips that parameter; configure thinking mode on the inference server instead.

### Embedding Models (ChromaDB RAG)
```yaml
infrastructure:
  # OpenAI-compatible embedding models
  embedding_model: "openai-compat://nomic-embed-text"           # 1536 dimensions
  embedding_model: "openai-compat://all-MiniLM-L6-v2"          # 384 dimensions
  embedding_model: "openai-compat://text-embedding-3-small"    # 1536 dimensions
  
  # With custom host
  embedding_model: "openai-compat://nomic-embed-text@192.168.1.100:11434"
  
  # Vector dimensions must match the model
  vector_dimensions: 1536  # for nomic-embed-text
  vector_dimensions: 384   # for all-MiniLM-L6-v2
```

### Unsupported Cloud Providers

Google, OpenAI, Anthropic, and OpenRouter provider URIs are not supported in the active runtime. Use `openai-compat://`, `lm_studio://`, or `llama_cpp://` model strings instead.

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
  initial_outline_writer: "openai-compat://llama3:70b?temperature=0.8"
  chapter_stage1_writer: "openai-compat://llama3:70b?temperature=0.8"

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

### ChromaDB RAG Configuration
```yaml
infrastructure:
  # High-quality embeddings (slower, more accurate)
  embedding_model: "openai-compat://nomic-embed-text"
  vector_dimensions: 1536
  similarity_threshold: 0.8
  
  # Fast embeddings (faster, good quality)
  embedding_model: "openai-compat://all-MiniLM-L6-v2"
  vector_dimensions: 384
  similarity_threshold: 0.7
  
  # Balanced approach
  embedding_model: "openai-compat://text-embedding-3-small"
  vector_dimensions: 1536
  similarity_threshold: 0.75
```

### Changing Embedding Models

**⚠️ Important**: If you change the embedding model after indexing wiki content, you'll need to rebuild or migrate embeddings.

**Before indexing content** (recommended):
1. Set your desired `embedding_model` in `config.yml`
2. Rebuild the affected ChromaDB story collections before generating more content

**After changing the embedding model** (if wiki content was already indexed):
1. Update `embedding_model` and `vector_dimensions` in `config.yml` to match the new model
2. Delete the affected story ChromaDB collection (the story directory contains a `.chromadb/` folder) so it will be re-created with the new embedding dimensions on next write
3. Re-index wiki content by running the story pipeline — the wiki tools will re-embed pages automatically as they are updated

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
```
