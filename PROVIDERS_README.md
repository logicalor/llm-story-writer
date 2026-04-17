# AI Story Writer - Model Providers

> **⚠️ NOTICE — LangChain support was removed.**
> The active runtime supports only local provider implementations: `openai-compat://`, `ollama://` (normalized to `openai-compat://`), `lm_studio://`, and `llama_cpp://`.
> Cloud provider schemes such as `google://`, `openrouter://`, `openai://`, and `anthropic://` are not supported.

This document provides an overview of all available model providers in the AI Story Writer application and how to configure and use them.

## Available Providers

The AI Story Writer supports three implemented model providers in the active runtime:

1. **Ollama Provider** - Local models through Ollama
2. **LM Studio Provider** - Local models through LM Studio  
3. **llama.cpp Provider** - Local models through llama.cpp server

## Provider Comparison

| Feature | Ollama | LM Studio | llama.cpp |
|---------|--------|-----------|-----------|
| **Local Models** | ✅ | ✅ | ✅ |
| **Cloud Models** | ❌ | ❌ | ❌ |
| **API Format** | Custom | OpenAI-compatible | HTTP API |
| **Model Management** | Programmatic | UI-based | Manual |
| **Cost** | Free | Free | Free |
| **Privacy** | 100% Local | 100% Local | 100% Local |
| **Setup Complexity** | Low | Low | Medium |
| **Model Variety** | High | High | High |
| **Multi-step Conversations** | ✅ | ✅ | ✅ |

## Quick Start

### 1. Choose Your Provider(s)

- **Local Only**: Use Ollama and/or LM Studio
- **High control**: Use llama.cpp for custom server setups
- **Mixed local approach**: Use different local providers for different tasks

### 2. Basic Configuration

```yaml
# config.yaml
# Local providers
model_api_base: "http://127.0.0.1:11434/v1"
lm_studio_host: "127.0.0.1:1234"

# Model configurations
models:
  # Local models
  scene_writer: "openai-compat://llama3:8b"
  logical_model: "lm_studio://mistral-7b-instruct"
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
model_api_base: "http://127.0.0.1:11434/v1"

models:
  scene_writer: "openai-compat://llama3:8b"
  logical_model: "openai-compat://mistral:7b"
```

**Model Format**:
```
openai-compat://model_name@host:port?param1=value1&param2=value2
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

`LangChainProvider` was removed in issue #26 and has no active implementation in `src/infrastructure/providers/`.

Unsupported cloud provider schemes:
- `google://`
- `openrouter://`
- `openai://`
- `anthropic://`

Use one of these supported schemes instead:
- `openai-compat://`
- `ollama://` (normalized internally to `openai_compatible`)
- `lm_studio://`
- `llama_cpp://`

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

All supported providers support **multi-step conversation with memory**, allowing you to build complex, contextual interactions.

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
- **Provider Agnostic**: Works with all supported providers

## Advanced Configuration

### Mixed Provider Strategy

Use different providers for different tasks:

```yaml
models:
  # Creative writing
  
  # Scene generation - use local models for privacy
  scene_writer: "openai-compat://llama3:8b"
  
  # Analysis
  logical_model: "llama_cpp://mistral-7b-instruct"
  
  # Revision - use local models for cost control
  revision_model: "lm_studio://mistral-7b-instruct"
```

### Provider-Specific Parameters

Each provider supports different parameters:

```yaml
models:
  # Ollama with custom parameters
  scene_writer: "openai-compat://llama3:8b?temperature=0.7"
  
  # LM Studio with OpenAI-style parameters
  logical_model: "lm_studio://mistral-7b-instruct?temperature=0.7"
  
  # llama.cpp with provider-specific parameters
  revision_model: "llama_cpp://mistral-7b-instruct?temperature=0.7"
```

### Environment Variables

The supported local providers do not require cloud API keys.

## Testing Your Setup

### Test Individual Providers

```bash
# Test Ollama
python test_ollama_provider.py

# Test LM Studio
python test_lm_studio_provider.py

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
  - Verify the selected local server exposes that model

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

1. **High-Quality Tasks**: Use your strongest local model
2. **High-Volume Tasks**: Use smaller local models through Ollama or LM Studio
3. **Specialized Tasks**: Use provider-specific local model setups
4. **Cost-Sensitive Tasks**: Keep workloads on local providers

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

### Best Practices
1. Use local models for sensitive content
2. Restrict local servers to trusted networks
3. Monitor model memory and disk usage
4. Verify host and port settings before long runs

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
  scene_writer: "openai-compat://llama3:8b"
```

## Support and Resources

### Documentation
- [Ollama Provider README](OLLAMA_PROVIDER_README.md)
- [LM Studio Provider README](LM_STUDIO_PROVIDER_README.md)

### Testing
- [Ollama Test Script](test_ollama_provider.py)
- [LM Studio Test Script](test_lm_studio_provider.py)

### Community
- Check GitHub issues for known problems
- Review provider-specific documentation
- Test with simple examples first

## Conclusion

The AI Story Writer's multi-provider architecture gives you maximum flexibility:

- **Use local models** for privacy and cost control
- **Mix and match** based on your needs
- **Switch easily** between providers
- **Scale up** as your needs grow

Start with local providers for development and production use. The shared model configuration format makes it easy to experiment and find the best combination for your workflow.
