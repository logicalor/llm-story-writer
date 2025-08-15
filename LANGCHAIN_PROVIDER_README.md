# LangChain Provider

This document explains how to set up and use the LangChain provider in the AI Story Writer application. The LangChain provider acts as a unified interface to multiple AI model providers, making it easy to switch between different services.

## Overview

The LangChain provider provides a unified interface to access various AI model providers through LangChain's ecosystem. This allows you to:

- Use cloud-based models (OpenAI, Anthropic, Google, etc.)
- Use local models (Ollama, LM Studio)
- Switch between providers without changing your code
- Access specialized models for different tasks

## Prerequisites

1. **Python Dependencies**: The provider will automatically install required LangChain packages
2. **API Keys**: For cloud-based providers (OpenAI, Anthropic, Google, HuggingFace)
3. **Local Services**: For local providers (Ollama, LM Studio)

## Supported Providers

### Cloud Providers
- **OpenAI**: GPT-3.5, GPT-4, and other OpenAI models
- **Anthropic**: Claude models
- **Google**: Gemini models
- **HuggingFace**: Various open-source models

### Local Providers
- **Ollama**: Local models running through Ollama
- **LM Studio**: Local models running through LM Studio
- **Generic**: Any OpenAI-compatible API endpoint

## Setup

### 1. Install Dependencies

The provider will automatically install required packages:
```bash
# These will be installed automatically when needed
pip install langchain langchain-openai langchain-anthropic langchain-community langchain-google-genai
```

### 2. Configure API Keys

Set environment variables for cloud providers:
```bash
export OPENAI_API_KEY="your-openai-api-key"
export ANTHROPIC_API_KEY="your-anthropic-api-key"
export GOOGLE_API_KEY="your-google-api-key"
export HUGGINGFACE_API_KEY="your-huggingface-api-key"
```

Or configure them in your config file:
```yaml
api_keys:
  openai: "your-openai-api-key"
  anthropic: "your-anthropic-api-key"
  google: "your-google-api-key"
  huggingface: "your-huggingface-api-key"
```

### 3. Start Local Services (if using)

- **Ollama**: Start Ollama and ensure models are downloaded
- **LM Studio**: Start LM Studio local server

## Configuration

### Model String Format

LangChain models use the following format:
```
langchain://provider:model_name@host:port?param1=value1&param2=value2
```

Examples:
- `langchain://openai:gpt-3.5-turbo` (OpenAI GPT-3.5)
- `langchain://anthropic:claude-3-haiku-20240307` (Anthropic Claude)
- `langchain://google:gemini-1.5-pro` (Google Gemini)
- `langchain://ollama:llama3:8b@localhost:11434` (Local Ollama)
- `langchain://lm_studio:llama-3-8b-instruct@localhost:1234` (Local LM Studio)

### Configuration Examples

```yaml
# Mix of cloud and local providers
ollama_host: "127.0.0.1:11434"
lm_studio_host: "127.0.0.1:1234"

api_keys:
  openai: "sk-..."
  anthropic: "sk-ant-..."
  google: "AIza..."

models:
  # Cloud models
  initial_outline_writer: "langchain://openai:gpt-4"
  chapter_outline_writer: "langchain://anthropic:claude-3-sonnet-20240229"
  scene_writer: "langchain://google:gemini-1.5-pro"
  
  # Local models
  logical_model: "langchain://ollama:llama3:70b"
  revision_model: "langchain://lm_studio:llama-3-8b-instruct"
  
  # Specialized models
  eval_model: "langchain://huggingface:microsoft/DialoGPT-medium"
```

## Features

### Supported Operations
- ✅ Text generation (with and without streaming)
- ✅ JSON generation
- ✅ Streaming text output
- ✅ Model availability checking
- ✅ Automatic provider selection
- ✅ Unified parameter interface
- ✅ **Multi-step conversation with memory**

### Key Benefits
1. **Unified Interface**: Same API for all providers
2. **Easy Switching**: Change providers without code changes
3. **Automatic Fallbacks**: Graceful handling of provider issues
4. **Rich Ecosystem**: Access to hundreds of models
5. **Local + Cloud**: Mix local and cloud models seamlessly
6. **Conversation Memory**: Maintain context across multiple exchanges

## Multi-step Conversation Feature

The LangChain provider includes a powerful multi-step conversation feature that maintains context and memory across multiple user interactions.

### How It Works

1. **Initialize**: Start with an optional system message and array of user messages
2. **Sequential Processing**: Process each user message one by one
3. **Memory Building**: Maintain conversation history and context
4. **Contextual Responses**: Each response builds on previous exchanges
5. **Final Output**: Return the final response with full conversation context

### Use Cases

- **Story Development**: Build complex narratives step by step
- **Problem Solving**: Work through multi-step problems with context
- **Creative Writing**: Develop ideas through iterative conversation
- **Analysis**: Build understanding through sequential questions
- **Planning**: Create detailed plans through guided conversation

### Example Workflow

```python
# Define the conversation flow
user_messages = [
    "I want to write a mystery novel.",
    "The detective is a retired police officer.",
    "The crime involves a missing painting.",
    "What are some red herrings I could include?",
    "How should the detective solve the case?",
    "Give me a complete plot summary."
]

# Set the context
system_message = "You are a creative writing coach helping develop a mystery novel."

# Execute the conversation
response = await provider.generate_multistep_conversation(
    user_messages=user_messages,
    model_config=model_config,
    system_message=system_message,
    debug=True
)
```

### Memory Management

The provider automatically manages conversation memory:
- **System Context**: Maintains the initial system message throughout
- **User Messages**: Stores each user input in sequence
- **Assistant Responses**: Captures each AI response for context
- **Full History**: Provides complete conversation context to the model

### Debug Information

When debug mode is enabled, you'll see:
- Step-by-step processing information
- Message content previews
- Response summaries
- Memory status updates
- Final response details

### Parameter Mapping

| Parameter | Description | Default |
|-----------|-------------|---------|
| `temperature` | Creativity level | 0.7 |
| `max_tokens` | Maximum response length | 16384 |
| `top_p` | Nucleus sampling | 0.9 |
| `seed` | Random seed for reproducibility | Random |

## Usage Examples

### Basic Text Generation
```python
from src.infrastructure.providers.langchain_provider import LangChainProvider
from src.domain.value_objects.model_config import ModelConfig

# Create provider
provider = LangChainProvider(api_keys={
    "openai": "your-key",
    "anthropic": "your-key"
})

# Create model config
model_config = ModelConfig(
    name="gpt-4",
    provider="langchain",
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
    name="gpt-4",
    provider="langchain",
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

### Multi-step Conversation with Memory
```python
# Create a conversation that builds context over multiple exchanges
user_messages = [
    "Hello! I want to write a science fiction story about time travel.",
    "The main character is a scientist who discovers a way to send messages to the past.",
    "What are some interesting complications that could arise from this discovery?",
    "How should the story end? Should the scientist succeed or fail?",
    "Give me a brief summary of the complete story arc."
]

system_message = "You are a helpful AI assistant helping to develop a story outline. Be creative and engaging."

response = await provider.generate_multistep_conversation(
    user_messages=user_messages,
    model_config=model_config,
    system_message=system_message,
    debug=True
)
```

This method:
- Maintains conversation context across all exchanges
- Processes each user message sequentially
- Builds memory of the conversation
- Returns the final response with full context

### Local Models
```python
# Ollama model
ollama_config = ModelConfig(
    name="llama3:70b",
    provider="langchain",
    host="http://localhost:11434",
    parameters={"temperature": 0.7}
)

# LM Studio model
lm_studio_config = ModelConfig(
    name="llama-3-8b-instruct",
    provider="langchain",
    host="http://localhost:1234",
    parameters={"temperature": 0.7}
)
```

## Provider-Specific Details

### OpenAI
- **Models**: GPT-3.5, GPT-4, GPT-4 Turbo
- **API Key**: Required
- **Rate Limits**: Based on your plan
- **Best For**: General purpose, creative writing

### Anthropic
- **Models**: Claude 3 Haiku, Sonnet, Opus
- **API Key**: Required
- **Rate Limits**: Based on your plan
- **Best For**: Analysis, reasoning, safety-focused tasks

### Google
- **Models**: Gemini 1.5 Pro, Gemini 1.5 Flash
- **API Key**: Required
- **Rate Limits**: Based on your plan
- **Best For**: Multimodal tasks, Google ecosystem integration

### HuggingFace
- **Models**: Thousands of open-source models
- **API Key**: Required for some models
- **Rate Limits**: Based on your plan
- **Best For**: Specialized tasks, open-source models

### Ollama
- **Models**: Any model available in Ollama
- **API Key**: Not required
- **Rate Limits**: None (local)
- **Best For**: Privacy, cost control, offline use

### LM Studio
- **Models**: Any model available in LM Studio
- **API Key**: Not required
- **Rate Limits**: None (local)
- **Best For**: Privacy, cost control, offline use

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure LangChain packages are installed
   - Check Python version compatibility

2. **API Key Issues**
   - Verify API keys are set correctly
   - Check environment variables
   - Ensure API keys have sufficient credits

3. **Model Not Found**
   - Verify model names are correct
   - Check if models are available in your region
   - Ensure you have access to the model

4. **Rate Limits**
   - Check your API plan limits
   - Implement retry logic if needed
   - Consider using local models for high-volume tasks

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
- Provider-specific information

## Testing

Run the test script to verify your setup:
```bash
python test_langchain_provider.py
```

This will test:
- Connection to various providers
- Model availability
- Basic text generation
- Provider functionality

## Performance Considerations

1. **Cloud vs Local**: Cloud models are faster but cost money; local models are free but slower
2. **Model Size**: Larger models are more capable but slower
3. **Caching**: LangChain provides caching for repeated requests
4. **Batch Processing**: Consider using smaller models for high-volume tasks

## Security

- **API Keys**: Store securely, never commit to version control
- **Local Models**: All data stays on your machine
- **Cloud Models**: Data may be processed on provider servers
- **Network**: Use HTTPS for all API calls

## Advanced Usage

### Custom Providers
You can extend the provider to support additional services by modifying the `_create_langchain_llm` method.

### Parameter Tuning
Experiment with different parameters for optimal results:
```python
parameters = {
    "temperature": 0.1,      # More focused
    "top_p": 0.8,           # More diverse
    "max_tokens": 2048,     # Longer responses
    "presence_penalty": 0.1, # Reduce repetition
    "frequency_penalty": 0.1 # Reduce repetition
}
```

### Model Switching
Easily switch between models for different tasks:
```python
# Creative writing
creative_model = ModelConfig.from_string("langchain://openai:gpt-4")

# Analysis
analysis_model = ModelConfig.from_string("langchain://anthropic:claude-3-sonnet-20240229")

# Local processing
local_model = ModelConfig.from_string("langchain://ollama:llama3:70b")
```

## Integration with AI Story Writer

The LangChain provider integrates seamlessly with the existing AI Story Writer architecture:

1. **Same Interface**: Uses the same ModelProvider interface
2. **Automatic Routing**: Models are automatically routed to the correct provider
3. **Configuration**: Works with existing configuration files
4. **Savepoints**: Compatible with the savepoint system
5. **Strategies**: Works with all existing story generation strategies

This makes it easy to enhance your story generation capabilities with access to the latest AI models while maintaining the existing workflow and architecture.
