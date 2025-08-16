# Llama.cpp Provider for AIStoryWriter

This document describes how to set up and use the llama.cpp provider in AIStoryWriter.

## Overview

The llama.cpp provider allows you to use models running on a local llama.cpp server. This is useful for running large language models locally without relying on external APIs.

## Prerequisites

1. **llama.cpp server running**: You need to have a llama.cpp server running locally
2. **Model files**: The models you want to use must be available to the llama.cpp server
3. **Python requests library**: The provider will automatically install this if needed

## Setup

### 1. Start the llama.cpp server

First, you need to start a llama.cpp server. You can do this in several ways:

#### Option A: Using the llama.cpp binary directly
```bash
# Download and build llama.cpp
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
make

# Start the server with a model
./server -m models/your-model.gguf -c 4096 --port 8080
```

#### Option B: Using Docker
```bash
docker run -d \
  --name llama-cpp-server \
  -p 8080:8080 \
  -v /path/to/models:/models \
  ghcr.io/ggerganov/llama.cpp:server \
  --model /models/your-model.gguf \
  --port 8080
```

#### Option C: Using the Python server
```bash
pip install llama-cpp-python[server]
python -m llama_cpp.server --model models/your-model.gguf --port 8080
```

### 2. Configure AIStoryWriter

Update your `config.md` file to include the llama.cpp host:

```yaml
infrastructure:
  llama_cpp_host: "127.0.0.1:8080"  # Default port for llama.cpp server
```

### 3. Use llama.cpp models in your configuration

You can now use llama.cpp models in your model configuration:

```yaml
models:
  initial_outline_writer: "llama_cpp://your-model-name"
  chapter_outline_writer: "llama_cpp://your-model-name"
  # ... other models
```

## Model Configuration

The llama.cpp provider supports various parameters that can be configured in your model configuration:

```yaml
models:
  my_model:
    provider: "llama_cpp"
    host: "127.0.0.1:8080"  # Optional, overrides infrastructure default
    parameters:
      temperature: 0.7
      top_p: 0.9
      top_k: 40
      repeat_penalty: 1.1
      n_ctx: 4096  # Context length
      seed: 42     # Optional seed for reproducible results
```

### Supported Parameters

- `temperature`: Controls randomness (0.0 = deterministic, 1.0 = very random)
- `top_p`: Nucleus sampling parameter
- `top_k`: Top-k sampling parameter
- `repeat_penalty`: Penalty for repeating tokens
- `n_ctx`: Context window size
- `seed`: Random seed for reproducible generation
- `stream`: Enable streaming responses

## API Endpoints

The llama.cpp provider expects the following API endpoints to be available:

- `POST /completion` - For text generation
- `GET /models` - For model availability checking

## Example Usage

### Basic Text Generation

```python
from src.infrastructure.providers.llama_cpp_provider import LlamaCppProvider

provider = LlamaCppProvider(host="127.0.0.1:8080")

messages = [
    {"role": "user", "content": "Write a short story about a robot."}
]

response = await provider.generate_text(
    messages=messages,
    model_config=model_config,
    debug=True
)
```

### JSON Generation

```python
response = await provider.generate_json(
    messages=messages,
    model_config=model_config,
    required_attributes=["title", "characters", "plot"],
    debug=True
)
```

### Streaming

```python
async for chunk in provider.stream_text(
    messages=messages,
    model_config=model_config
):
    print(chunk, end="", flush=True)
```

## Troubleshooting

### Common Issues

1. **Connection refused**: Make sure the llama.cpp server is running on the specified port
2. **Model not found**: Ensure the model is loaded in the llama.cpp server
3. **Timeout errors**: Increase the timeout in the provider or check server performance

### Debug Mode

Enable debug mode to see detailed information about requests and responses:

```python
response = await provider.generate_text(
    messages=messages,
    model_config=model_config,
    debug=True
)
```

### Checking Model Availability

```python
is_available = await provider.is_model_available(model_config)
print(f"Model available: {is_available}")
```

## Performance Considerations

- **Context length**: Larger context windows use more memory
- **Batch size**: Adjust based on your hardware capabilities
- **Model size**: Larger models provide better quality but require more resources

## Security Notes

- The llama.cpp server runs locally, so your data stays on your machine
- No API keys or external services are required
- Consider firewall rules if running on a network-accessible machine

## Integration with AIStoryWriter

The llama.cpp provider integrates seamlessly with the existing AIStoryWriter architecture:

- Supports all story generation strategies
- Works with the savepoint system
- Compatible with the prompt management system
- Supports both streaming and non-streaming modes

## Example Configuration

Here's a complete example configuration for using llama.cpp:

```yaml
---
models:
  initial_outline_writer: "llama_cpp://llama-2-7b-chat"
  chapter_outline_writer: "llama_cpp://llama-2-7b-chat"
  chapter_stage1_writer: "llama_cpp://llama-2-7b-chat"
  chapter_stage2_writer: "llama_cpp://llama-2-7b-chat"
  chapter_stage3_writer: "llama_cpp://llama-2-7b-chat"
  chapter_stage4_writer: "llama_cpp://llama-2-7b-chat"
  chapter_revision_writer: "llama_cpp://llama-2-7b-chat"
  revision_model: "llama_cpp://llama-2-7b-chat"
  eval_model: "llama_cpp://llama-2-7b-chat"
  info_model: "llama_cpp://llama-2-7b-chat"
  scrub_model: "llama_cpp://llama-2-7b-chat"
  checker_model: "llama_cpp://llama-2-7b-chat"
  translator_model: "llama_cpp://llama-2-7b-chat"
  sanity_model: "llama_cpp://llama-2-7b-chat"
  logical_model: "llama_cpp://llama-2-7b-chat"
  scene_writer: "llama_cpp://llama-2-7b-chat"

infrastructure:
  llama_cpp_host: "127.0.0.1:8080"
  context_length: 4096
  randomize_seed: true
---
```

## Support

For issues specific to the llama.cpp provider:

1. Check that the llama.cpp server is running and accessible
2. Verify the model is loaded in the server
3. Check the server logs for any errors
4. Ensure the API endpoints are responding correctly

For general AIStoryWriter support, refer to the main README.md file.
