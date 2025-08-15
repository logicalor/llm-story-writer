# LM Studio Provider

This document explains how to set up and use the LM Studio provider in the AI Story Writer application.

## Overview

The LM Studio provider allows you to use local models running through LM Studio instead of or alongside Ollama. LM Studio provides a local API server that's compatible with OpenAI's API format.

## Prerequisites

1. **LM Studio Application**: Download and install LM Studio from [https://lmstudio.ai/](https://lmstudio.ai/)
2. **Python Dependencies**: The provider will automatically install the `requests` package if needed

## Setup

### 1. Start LM Studio

1. Open the LM Studio application
2. Download a model of your choice (e.g., Llama 3, Mistral, etc.)
3. Start the local server:
   - Click on "Local Server" in the left sidebar
   - Click "Start Server"
   - The server will start on `127.0.0.1:1234` by default

### 2. Configure the Application

Add LM Studio configuration to your config file:

```yaml
# Example config with both Ollama and LM Studio
ollama_host: "127.0.0.1:11434"
lm_studio_host: "127.0.0.1:1234"

models:
  # Ollama models
  initial_outline_writer: "ollama://llama3:70b"
  chapter_outline_writer: "ollama://llama3:70b"
  
  # LM Studio models
  scene_writer: "lm_studio://llama-3-8b-instruct"
  logical_model: "lm_studio://mistral-7b-instruct"
```

### 3. Model String Format

LM Studio models use the following format:
```
lm_studio://model_name@host:port?param1=value1&param2=value2
```

Examples:
- `lm_studio://llama-3-8b-instruct` (uses default host)
- `lm_studio://mistral-7b-instruct@192.168.1.100:1234` (custom host)
- `lm_studio://llama-3-70b-instruct?temperature=0.7&max_tokens=2048` (with parameters)

## Features

### Supported Operations
- ✅ Text generation (with and without streaming)
- ✅ JSON generation
- ✅ Streaming text output
- ✅ Model availability checking
- ✅ Custom parameters (temperature, max_tokens, etc.)

### Key Differences from Ollama
1. **API Format**: Uses OpenAI-compatible API instead of Ollama's custom API
2. **Model Management**: Models are managed through LM Studio's interface, not programmatically
3. **Host Default**: Defaults to `127.0.0.1:1234` instead of `127.0.0.1:11434`
4. **Parameter Names**: Uses OpenAI-style parameter names (e.g., `max_tokens` instead of `num_ctx`)

### Parameter Mapping

| Ollama Parameter | LM Studio Parameter | Notes |
|------------------|-------------------|-------|
| `num_ctx` | `max_tokens` | Context length |
| `temperature` | `temperature` | Same |
| `top_p` | `top_p` | Same |
| `seed` | `seed` | Same |
| `format` | `response_format` | For JSON responses |

## Usage Examples

### Basic Text Generation
```python
from src.infrastructure.providers.lm_studio_provider import LMStudioProvider
from src.domain.value_objects.model_config import ModelConfig

# Create provider
provider = LMStudioProvider(host="127.0.0.1:1234")

# Create model config
model_config = ModelConfig(
    name="llama-3-8b-instruct",
    provider="lm_studio",
    parameters={"temperature": 0.7, "max_tokens": 1000}
)

# Generate text
messages = [{"role": "user", "content": "Write a short story."}]
response = await provider.generate_text(messages, model_config)
```

### JSON Generation
```python
# For JSON responses, the provider automatically sets response_format
model_config = ModelConfig(
    name="llama-3-8b-instruct",
    provider="lm_studio",
    parameters={"temperature": 0.0}  # Low temperature for consistent JSON
)

response = await provider.generate_json(
    messages, 
    model_config, 
    required_attributes=["title", "content"]
)
```

### Streaming
```python
async for chunk in provider.stream_text(messages, model_config):
    print(chunk, end="", flush=True)
```

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Ensure LM Studio is running
   - Check that the local server is started
   - Verify the host and port in your configuration

2. **Model Not Found**
   - Download the model in LM Studio first
   - Check the exact model name (case-sensitive)
   - Ensure the model is loaded in LM Studio

3. **Timeout Errors**
   - Increase timeout values in the provider
   - Check if the model is too large for your hardware
   - Consider using a smaller model

### Debug Mode

Enable debug mode to see detailed information:
```python
response = await provider.generate_text(
    messages, 
    model_config, 
    debug=True
)
```

This will show:
- Full prompt messages
- Token count estimates
- Request details
- Response processing

## Testing

Run the test script to verify your setup:
```bash
python test_lm_studio_provider.py
```

This will test:
- Connection to LM Studio
- Model availability
- Basic text generation
- Provider functionality

## Configuration Files

### Example Config with Both Providers
```yaml
# config.yaml
ollama_host: "127.0.0.1:11434"
lm_studio_host: "127.0.0.1:1234"

models:
  # Use Ollama for some tasks
  initial_outline_writer: "ollama://llama3:70b"
  chapter_outline_writer: "ollama://llama3:70b"
  
  # Use LM Studio for others
  scene_writer: "lm_studio://llama-3-8b-instruct"
  logical_model: "lm_studio://mistral-7b-instruct"
  
  # Mix and match as needed
  revision_model: "ollama://llama3:70b"
  eval_model: "lm_studio://llama-3-8b-instruct"
```

## Performance Considerations

1. **Model Loading**: LM Studio loads models into memory, which can take time
2. **Hardware Requirements**: Larger models require more RAM and VRAM
3. **Batch Processing**: Consider using smaller models for faster generation
4. **Caching**: LM Studio keeps models in memory between requests

## Security

- The LM Studio provider only connects to localhost by default
- No data is sent to external services
- All processing happens locally on your machine
- Consider firewall rules if using custom network configurations
