# AI Story Writer 📚✨

A modern, clean AI story generation application built with clean architecture principles. Generate full-length novels with AI using multiple model providers.

[![Discord](https://img.shields.io/discord/1255847829763784754?color=7289DA&label=Discord&logo=discord&logoColor=white)](https://discord.gg/R2SySWDr2s)

## 🚀 Features

- **Clean Architecture**: Built with domain-driven design and clean architecture principles
- **Multiple Model Providers**: Support for Ollama, LM Studio, LangChain, llama.cpp, Google, OpenRouter, and more
- **Async/Await**: Full async support for better performance
- **Type Safety**: Comprehensive type hints and validation
- **Structured Logging**: Professional logging with levels and structured data
- **Dependency Injection**: Clean dependency management and testability
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
2. **Ollama** installed and running (for local models)
3. **API Keys** (optional, for cloud providers)

### Installation

```bash
# Clone the repository
git clone https://github.com/datacrystals/AIStoryWriter.git
cd AIStoryWriter

# Install dependencies
pip install -r requirements.txt

# Install the application
pip install -e src/
```

### Basic Usage

```bash
# Generate a story from a prompt file
python src/main.py Prompts/YourPrompt.txt
```

The application will use all configuration options defined in `config.md`.

## 🧰 Configuration

All configuration options are defined in the YAML frontmatter of `config.md`. You can modify these values to customize the behavior of the application.

### Model Configuration

The application supports multiple model providers with a unified format:

```yaml
models:
  initial_outline_writer: "ollama://llama3:70b"
  chapter_stage1_writer: "ollama://llama3:70b@192.168.1.100:11434"
  info_model: "ollama://llama3:70b?temperature=0.7"
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
# Run all tests
pytest tests/

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# Run with coverage
pytest --cov=src tests/
```

## 📁 Project Structure

```
AIStoryWriter/
├── src/                    # Main application code
│   ├── domain/            # Business logic and entities
│   ├── application/       # Use cases and services
│   ├── infrastructure/    # External concerns
│   ├── presentation/      # CLI and API interfaces
│   └── config/           # Configuration management
├── tests/                 # Test suite
├── Prompts/              # Story prompts
├── Stories/              # Generated stories
├── SavePoints/           # Generation savepoints
├── Logs/                 # Application logs
└── docs/                 # Documentation
```

## 🔧 Development

### Adding a New Model Provider

1. Create a new provider in `src/infrastructure/providers/`
2. Implement the `ModelProvider` interface
3. Register it in the dependency injection container
4. Add tests

### Adding a New Storage Backend

1. Create a new storage implementation in `src/infrastructure/storage/`
2. Implement the `StorageProvider` interface
3. Register it in the dependency injection container
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

---

Join us in shaping the future of AI-assisted storytelling! 🖋️🤖
