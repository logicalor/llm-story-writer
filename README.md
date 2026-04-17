# AI Story Writer 📚✨

A modern, clean AI story generation application built with clean architecture principles. Generate full-length novels with AI using multiple model providers.

[![Discord](https://img.shields.io/discord/1255847829763784754?color=7289DA&label=Discord&logo=discord&logoColor=white)](https://discord.gg/R2SySWDr2s)

## 🚀 Features

- **Clean Architecture**: Built with domain-driven design and clean architecture principles
- **Multiple Local Model Providers**: Support for Ollama, LM Studio, and llama.cpp
- **Async/Await**: Full async support for better performance
- **Type Safety**: Comprehensive type hints and validation
- **ChromaDB-backed wiki retrieval**: Per-story semantic search over progressive wiki memory
- **Extensible Design**: Easy to add new features and providers
- **Generate medium to full-length novels**: Produce substantial stories with coherent narratives
- **Automatic model downloading**: The system can automatically download required models via Ollama
- **Translation support**: Translate stories and prompts to multiple languages
- **Savepoint system**: Resume generation from any point

## 🏗️ Architecture

This application is built using clean architecture principles:

```
src/
├── domain/              # Business logic and entities
├── application/         # Use cases and services
├── infrastructure/      # External concerns (providers, storage, logging)
├── presentation/        # CLI and API interfaces
└── config/             # Configuration management
```

## 🏁 Quick Start

### Prerequisites

1. **Python 3.8+** installed
2. **OpenCode** installed
3. **Ollama** installed and running (for local models)

### Installation

```bash
# Clone the repository
git clone https://github.com/datacrystals/AIStoryWriter.git
cd AIStoryWriter

# Install OpenCode first
# Follow your platform's OpenCode install instructions, then verify:
opencode --version

# Configure Ollama and pull the models referenced by config.md
ollama serve

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage (OpenCode TUI)

The application uses OpenCode for an interactive story generation experience:

```bash
# Start OpenCode in the project root
opencode

# In the TUI, use slash commands:
/new-story prompts/YourPrompt.txt    # Initialize and start a new story
/continue [story-name]               # Resume from last savepoint
/status                              # Show generation progress
```

The application will use all configuration options defined in `config.md`.

## 🧰 Configuration

All configuration options are defined in the YAML frontmatter of `config.md`. You can modify these values to customize the behavior of the application.

### Model Configuration

The application supports multiple model providers with a unified format:

```yaml
models:
  initial_outline_writer: "openai-compat://llama3:70b"
  chapter_stage1_writer: "openai-compat://llama3:70b@192.168.1.100:11434"
  info_model: "openai-compat://llama3:70b?temperature=0.7"
```

### Generation Settings

```yaml
generation:
  seed: 12
  outline_min_revisions: 2
  outline_max_revisions: 5
  chapter_min_revisions: 1
  chapter_max_revisions: 3
  enable_final_edit: true
  stream: false
  debug: false
  strategy: "outline-chapter"  # or "stream-of-consciousness"
```

### Story Writing Strategies

The application supports multiple story writing strategies:

- **`outline-chapter`** (default): Generates detailed outlines first, then writes chapters based on the outline structure
- **`stream-of-consciousness`**: Generates stories in a flowing, associative narrative style

To change strategies, update the `strategy` option in the generation settings above.

See `src/application/strategies/README.md` for detailed information about creating custom strategies.

### Environment Variables

Create a `.env` file for API keys:

```bash
# .env
GOOGLE_API_KEY=your_google_api_key
OPENROUTER_API_KEY=your_openrouter_api_key
```

For detailed configuration options, see [config.md](config.md).

## 🧪 Testing

```bash
# Run default fast test suite (unit tests only)
pytest

# Run unit tests explicitly
pytest tests/unit/ -v

# Run integration tests explicitly (live LLM required)
pytest tests/integration/ -v -m integration

# Run the full end-to-end integration file with a longer timeout
pytest tests/integration/test_e2e_opencode.py -v -m integration --timeout=7200

# Run with coverage
pytest --cov=src tests/unit tests/integration
```

Integration tests exercise the full story-generation pipeline with wiki support against a live OpenAI-compatible endpoint. Set `LLM_API_BASE` to override the default endpoint (`http://localhost:11434/v1`). A full run typically takes 30 to 90 minutes.

See [docs/testing/integration-tests.md](docs/testing/integration-tests.md) for setup details, runtime expectations, and manual verification guidance.

## 📁 Project Structure

```
llm-story-writer/
├── src/                          # Python domain logic (clean architecture)
│   ├── domain/                  # Business logic and entities
│   ├── application/             # Use cases and services
│   ├── infrastructure/          # External concerns (providers, storage)
│   ├── presentation/            # CLI and API interfaces
│   ├── tools/                   # Python tool implementations
│   └── config/                  # Configuration management
├── .opencode/                   # OpenCode agentic system
│   ├── agents/                  # Agent definitions (orchestrator, scene-writer, etc.)
│   ├── tools/                   # TypeScript tool wrappers
│   ├── skills/                  # Reusable skills
│   ├── commands/                # TUI slash commands (/new-story, /continue, etc.)
│   └── plugins/                 # OpenCode plugins
├── prompts/                     # Prompt templates (relocated from src/)
│   ├── chapters/
│   ├── characters/
│   ├── outline/
│   ├── scenes/
│   └── ...
├── stories/<name>/              # Per-story storage
│   ├── chapters/                # Generated chapter content
│   ├── characters/              # Character sheets (JSON)
│   ├── settings/                # Setting/location sheets (JSON)
│   ├── savepoints/              # Generation savepoints
│   └── wiki/                    # Progressive wiki memory
│       ├── characters/
│       ├── locations/
│       ├── events/
│       └── ...
├── .chromadb/                   # ChromaDB vector storage (per-story collections)
├── legacy/                      # Archived original codebase (reference only)
├── tests/                       # Test suite
└── docs/                        # Documentation
```

## 🤖 OpenCode Integration

This project uses a **hybrid agent-tool architecture** where OpenCode agents handle orchestration and human interaction, while Python scripts (wrapped as OpenCode tools) handle deterministic domain logic. The architecture preserves clean architecture principles in the Python domain layer while leveraging OpenCode's agentic capabilities for creative tasks.

Key components:
- **Agents** (`.opencode/agents/`): story-orchestrator, outline-planner, chapter-writer
- **Tools** (`.opencode/tools/`): TypeScript wrappers that call Python scripts in `src/tools/`
- **Skills** (`.opencode/skills/`): Reusable instructions for pipeline phases, wiki maintenance, etc.
- **Commands** (`.opencode/commands/`): TUI slash commands like `/new-story`, `/continue`, `/status`

## 📚 Wiki System

The progressive wiki memory system maintains structured story knowledge using markdown pages with YAML frontmatter:

- **Page Types**: Characters, locations, events, factions, items, plot-threads, world-rules, themes, relationships, timeline, chapters
- **Detail Levels**: L1 (headline, ~30 tokens), L2 (brief, ~150 tokens), L3 (full, ~500 tokens)
- **Confidence Taxonomy**: `verified` (explicitly stated), `planned` (outlined but not yet written), `speculative` (inferred or implied)
- **Cross-References**: Wiki pages use `[[wikilink]]` syntax to reference related entities

The wiki is automatically updated after each scene by the wiki-maintainer agent, ensuring consistent story state throughout generation.

## 🔍 ChromaDB RAG

Semantic search for context retrieval using ChromaDB vector collections:

- **Per-Story Collections**: Each story has its own isolated ChromaDB collection
- **Wiki Embedding**: Wiki pages are automatically embedded when created or updated
- **Hybrid Retrieval**: Combines entity matching, metadata filtering, semantic search, and wikilink traversal
- **Context Assembly**: The `wiki-snapshot` tool assembles token-budgeted context for each scene using detail levels L1/L2/L3

## 🔧 Development

### Adding a New Model Provider

1. Create a new provider in `src/infrastructure/providers/`
2. Implement the `ModelProvider` interface
3. Wire it into the relevant tool or service entry point
4. Add tests

### Adding a New Storage Backend

1. Create a new storage implementation in `src/infrastructure/storage/`
2. Implement the `StorageProvider` interface
3. Wire it into the consuming tool or service
4. Add tests

### Adding New Features

1. Add domain entities and value objects in `src/domain/`
2. Create application services in `src/application/services/`
3. Add infrastructure implementations as needed
4. Update CLI interface in `src/presentation/cli/`
5. Add comprehensive tests

## 🚀 Performance

- **Async Operations**: All I/O operations are async for better performance
- **Model Caching**: Automatic model downloading and caching
- **Resource Management**: Proper cleanup and resource handling
- **Streaming Support**: Stream model responses for real-time feedback

## 🔍 Monitoring

- **Structured Logging**: JSON-formatted logs with metadata
- **Performance Metrics**: Generation time, word count, tokens per second
- **Error Tracking**: Comprehensive error handling and reporting
- **Debug Mode**: Detailed logging for troubleshooting

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Clone and setup
git clone https://github.com/datacrystals/AIStoryWriter.git
cd AIStoryWriter
pip install -r requirements.txt
pip install -e src/

# Run tests
pytest tests/

# Run linting
flake8 src/
mypy src/
```

## 📄 License

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0). See the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Discord**: [Join our Discord server](https://discord.gg/R2SySWDr2s)
- **Issues**: [GitHub Issues](https://github.com/datacrystals/AIStoryWriter/issues)
- **Discussions**: [GitHub Discussions](https://github.com/datacrystals/AIStoryWriter/discussions)

## 🎯 Roadmap

- [ ] Web API for story generation
- [ ] Database storage backends
- [ ] Additional model providers (OpenAI, Anthropic)
- [ ] Plugin system for custom features
- [ ] Distributed generation support
- [ ] Real-time collaboration features
- [ ] Advanced story analytics
- [ ] Multi-language support

## 🗃️ Legacy Reference

The `legacy/` directory preserves the original PostgreSQL/LangChain-based architecture for reference during the OpenCode and ChromaDB migration. Active development happens in `src/`, `.opencode/`, `prompts/`, and `stories/`.

---

Join us in shaping the future of AI-assisted storytelling! 🖋️🤖
