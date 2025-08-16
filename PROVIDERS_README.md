# AI Story Writer - Model Providers

This document provides an overview of all available model providers in the AI Story Writer application and how to configure and use them.

## Available Providers

The AI Story Writer supports four main model providers, each with different capabilities and use cases:

1. **Ollama Provider** - Local models through Ollama
2. **LM Studio Provider** - Local models through LM Studio  
3. **LangChain Provider** - Unified interface to multiple providers
4. **llama.cpp Provider** - Local models through llama.cpp server

## Provider Comparison

| Feature | Ollama | LM Studio | LangChain | llama.cpp |
|---------|--------|-----------|-----------|-----------|
| **Local Models** | ✅ | ✅ | ✅ | ✅ |
| **Cloud Models** | ❌ | ❌ | ✅ | ❌ |
| **API Format** | Custom | OpenAI-compatible | Multiple | HTTP API |
| **Model Management** | Programmatic | UI-based | Provider-specific | Manual |
| **Cost** | Free | Free | Variable | Free |
| **Privacy** | 100% Local | 100% Local | Configurable | 100% Local |
| **Setup Complexity** | Low | Low | Medium | Medium |
| **Model Variety** | High | High | Very High | High |
| **Multi-step Conversations** | ✅ | ✅ | ✅ | ✅ |

## Quick Start

### 1. Choose Your Provider(s)

- **Local Only**: Use Ollama and/or LM Studio
- **Cloud + Local**: Use LangChain with API keys
- **Mixed Approach**: Use all three for different tasks

### 2. Basic Configuration

```yaml
# config.yaml
# Local providers
ollama_host: "127.0.0.1:11434"
lm_studio_host: "127.0.0.1:1234"

# Cloud provider API keys
api_keys:
  openai: "sk-..."
  anthropic: "sk-ant-..."
  google: "AIza..."

# Model configurations
models:
  # Local models
  scene_writer: "ollama://llama3:8b"
  logical_model: "lm_studio://mistral-7b-instruct"
  
  # Cloud models via LangChain
  initial_outline_writer: "langchain://openai:gpt-4"
  chapter_outline_writer: "langchain://anthropic:claude-3-sonnet-20240229"
```

## Provider Details

### Ollama Provider

**Best for**: Local models, privacy, cost control

**Setup**:
1. Install Ollama: https://ollama.ai/
2. Download models: `ollama pull llama3:8b`
3. Start service: `ollama serve`

**Configuration**:
```yaml
ollama_host: "127.0.0.1:11434"

models:
  scene_writer: "ollama://llama3:8b"
  logical_model: "ollama://mistral:7b"
```

**Model Format**:
```
ollama://model_name@host:port?param1=value1&param2=value2
```

### LM Studio Provider

**Best for**: Local models, easy UI, OpenAI compatibility

**Setup**:
1. Download LM Studio: https://lmstudio.ai/
2. Download models through the UI
3. Start local server (port 1234)

**Configuration**:
```yaml
lm_studio_host: "127.0.0.1:1234"

models:
  scene_writer: "lm_studio://llama-3-8b-instruct"
  logical_model: "lm_studio://mistral-7b-instruct"
```

**Model Format**:
```
lm_studio://model_name@host:port?param1=value1&param2=value2
```

### LangChain Provider

**Best for**: Cloud models, unified interface, maximum flexibility

**Setup**:
1. Get API keys for desired services
2. Set environment variables or config file
3. Install LangChain packages (automatic)

**Configuration**:
```yaml
api_keys:
  openai: "sk-..."
  anthropic: "sk-ant-..."
  google: "AIza..."

models:
  # Cloud models
  initial_outline_writer: "langchain://openai:gpt-4"
  chapter_outline_writer: "langchain://anthropic:claude-3-sonnet-20240229"
  
  # Local models via LangChain
  scene_writer: "langchain://ollama:llama3:8b@localhost:11434"
  logical_model: "langchain://lm_studio:mistral-7b-instruct@localhost:1234"
```

**Model Format**:
```
langchain://provider:model_name@host:port?param1=value1&param2=value2
```

### llama.cpp Provider

**Best for**: Local models, high performance, custom server setup

**Setup**:
1. Build or download llama.cpp: https://github.com/ggerganov/llama.cpp
2. Start the server: `./server -m models/your-model.gguf --port 8080`
3. Or use Docker: `docker run -p 8080:8080 ghcr.io/ggerganov/llama.cpp:server`

**Configuration**:
```yaml
llama_cpp_host: "127.0.0.1:8080"

models:
  scene_writer: "llama_cpp://llama-2-7b-chat"
  logical_model: "llama_cpp://mistral-7b-instruct"
```

**Model Format**:
```
llama_cpp://model_name@host:port?param1=value1&param2=value2
```

**Supported Parameters**:
- `temperature`: Controls randomness (0.0-1.0)
- `top_p`: Nucleus sampling parameter
- `top_k`: Top-k sampling parameter
- `repeat_penalty`: Penalty for repeating tokens
- `n_ctx`: Context window size
- `seed`: Random seed for reproducible generation

## Multi-step Conversation Feature

All four providers support **multi-step conversation with memory**, allowing you to build complex, contextual interactions.

### How It Works

1. **Initialize**: Provide an array of user messages and optional system message
2. **Sequential Processing**: Each message is processed in order with full context
3. **Memory Building**: Conversation history is maintained throughout
4. **Contextual Responses**: Each response builds on previous exchanges
5. **Final Output**: Return the complete response with full conversation context

### Example Usage

```python
# Define conversation flow
user_messages = [
    "I want to write a mystery novel.",
    "The detective is a retired police officer.",
    "The crime involves a missing painting.",
    "What are some red herrings I could include?",
    "Give me a complete plot summary."
]

system_message = "You are a creative writing coach helping develop a mystery novel."

# Non-streaming conversation
response = await provider.generate_multistep_conversation(
    user_messages=user_messages,
    model_config=model_config,
    system_message=system_message,
    debug=True
)

# Streaming conversation (respects generation.stream setting)
response = await provider.generate_multistep_conversation(
    user_messages=user_messages,
    model_config=model_config,
    system_message=system_message,
    debug=True,
    stream=True  # Enable real-time streaming output
)
```

### Use Cases

- **Story Development**: Build complex narratives step by step
- **Problem Solving**: Work through multi-step problems with context
- **Creative Writing**: Develop ideas through iterative conversation
- **Analysis**: Build understanding through sequential questions
- **Planning**: Create detailed plans through guided conversation

### Benefits

- **Context Awareness**: Each response considers the full conversation
- **Memory Management**: Automatic conversation history tracking
- **Sequential Logic**: Natural flow from simple to complex
- **Debug Support**: Step-by-step processing visibility
- **Provider Agnostic**: Works with all four providers

## Advanced Configuration

### Mixed Provider Strategy

Use different providers for different tasks:

```yaml
models:
  # Creative writing - use powerful cloud models
  initial_outline_writer: "langchain://openai:gpt-4"
  chapter_outline_writer: "langchain://anthropic:claude-3-sonnet-20240229"
  
  # Scene generation - use local models for privacy
  scene_writer: "ollama://llama3:8b"
  
  # Analysis - use specialized models
  logical_model: "langchain://google:gemini-1.5-pro"
  
  # Revision - use local models for cost control
  revision_model: "lm_studio://mistral-7b-instruct"
```

### Provider-Specific Parameters

Each provider supports different parameters:

```yaml
models:
  # Ollama with custom parameters
  scene_writer: "ollama://llama3:8b?temperature=0.7"
  
  # LM Studio with OpenAI-style parameters
  logical_model: "lm_studio://mistral-7b-instruct?temperature=0.7"
  
  # LangChain with provider-specific parameters
  cloud_model: "langchain://openai:gpt-4?temperature=0.7"
```

### Environment Variables

Set API keys via environment variables:

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="AIza..."
export HUGGINGFACE_API_KEY="hf_..."
```

## Testing Your Setup

### Test Individual Providers

```bash
# Test Ollama
python test_ollama_provider.py

# Test LM Studio
python test_lm_studio_provider.py

# Test LangChain
python test_langchain_provider.py
```

### Test Configuration

```bash
# Test your config file
python -c "
from src.config.config_loader import ConfigLoader
config = ConfigLoader.load_config('config.yaml')
print('Configuration loaded successfully!')
print(f'Models: {list(config.models.keys())}')
"
```

## Troubleshooting

### Common Issues

1. **Provider Not Found**
   - Check provider name spelling
   - Ensure provider is imported in container.py
   - Verify provider is added to valid_providers list

2. **Connection Errors**
   - Check host/port configuration
   - Ensure local services are running
   - Verify network connectivity

3. **Model Not Available**
   - Check model name spelling
   - Ensure model is downloaded/available
   - Verify API keys for cloud models

4. **Import Errors**
   - Install required packages
   - Check Python version compatibility
   - Verify import paths

### Debug Mode

Enable debug mode to see detailed information:

```python
response = await provider.generate_text(
    messages, 
    model_config, 
    debug=True
)
```

### Provider Logs

Each provider logs detailed information:
- Model selection
- Request details
- Response processing
- Error information

## Performance Optimization

### Model Selection Strategy

1. **High-Quality Tasks**: Use cloud models (GPT-4, Claude, Gemini)
2. **High-Volume Tasks**: Use local models (Ollama, LM Studio)
3. **Specialized Tasks**: Use specialized models (HuggingFace)
4. **Cost-Sensitive Tasks**: Use local models

### Caching and Reuse

- Models are cached within each provider
- Reuse model instances when possible
- Consider model unloading for memory management

### Parallel Processing

- Different providers can run in parallel
- Use async/await for concurrent requests
- Consider provider-specific rate limits

## Security Considerations

### Local Providers (Ollama, LM Studio)
- ✅ 100% private - no data leaves your machine
- ✅ No API keys required
- ✅ Full control over models and data

### Cloud Providers (via LangChain)
- ⚠️ Data may be processed on provider servers
- ⚠️ API keys required - store securely
- ⚠️ Rate limits and usage tracking
- ✅ Use HTTPS for all connections

### Best Practices
1. Store API keys in environment variables
2. Never commit API keys to version control
3. Use local models for sensitive content
4. Monitor API usage and costs

## Migration Guide

### From Single Provider to Multiple

1. **Keep existing configuration**
2. **Add new provider configurations**
3. **Test new providers individually**
4. **Gradually migrate models**
5. **Monitor performance and costs**

### Provider Switching

```yaml
# Before: Single provider
models:
  scene_writer: "ollama://llama3:8b"

# After: Multiple providers
models:
  scene_writer: "langchain://ollama:llama3:8b@localhost:11434"
  # or
  scene_writer: "ollama://llama3:8b"
```

## Support and Resources

### Documentation
- [Ollama Provider README](OLLAMA_PROVIDER_README.md)
- [LM Studio Provider README](LM_STUDIO_PROVIDER_README.md)
- [LangChain Provider README](LANGCHAIN_PROVIDER_README.md)

### Testing
- [Ollama Test Script](test_ollama_provider.py)
- [LM Studio Test Script](test_lm_studio_provider.py)
- [LangChain Test Script](test_langchain_provider.py)

### Community
- Check GitHub issues for known problems
- Review provider-specific documentation
- Test with simple examples first

## Conclusion

The AI Story Writer's multi-provider architecture gives you maximum flexibility:

- **Use local models** for privacy and cost control
- **Use cloud models** for quality and speed
- **Mix and match** based on your needs
- **Switch easily** between providers
- **Scale up** as your needs grow

Start with local providers for development and testing, then add cloud providers for production use. The unified interface makes it easy to experiment and find the best combination for your workflow.
