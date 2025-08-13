# Story Writing Strategies

This directory contains the story writing strategies that can be used by the AI Story Writer application. The strategy pattern allows for different approaches to story generation, making the system flexible and extensible.

## Overview

The strategy system allows you to:
- **Swap story writing approaches** without changing the core application
- **Add new strategies** as plugins
- **Configure different strategies** via the `config.md` file
- **Maintain clean separation** between story logic and application logic
- **Organize prompts by strategy** with dedicated prompt directories

## Directory Structure

```
src/application/strategies/
├── README.md                           # This documentation
├── strategy_factory.py                 # Strategy management
├── outline_chapter/                    # Outline-chapter strategy
│   ├── strategy.py                     # Main strategy implementation
│   └── prompts/                        # Strategy-specific prompts
│       ├── extract_story_start_date.md
│       ├── extract_base_context.md
│       ├── generate_story_elements.md
│       ├── generate_initial_outline.md
│       ├── generate_chapter_list.md
│       ├── count_chapters.md
│       ├── get_chapter_outline.md
│       ├── get_previous_chapter_recap.md
│       ├── generate_chapter_content.md
│       ├── generate_chapter_title.md
│       ├── generate_title.md
│       ├── generate_summary.md
│       └── generate_tags.md
├── stream_of_consciousness/            # Stream-of-consciousness strategy
│   ├── strategy.py                     # Main strategy implementation
│   └── prompts/                        # Strategy-specific prompts
│       ├── outline.md
│       ├── content.md
│       └── metadata.md

```

## Available Strategies

### 1. Outline-Chapter Strategy (`outline-chapter`)
- **Description**: Generates a detailed outline first, then writes chapters based on the outline structure
- **Best for**: Traditional narrative stories with clear structure
- **Process**: 
  1. Extract story elements and context
  2. Generate detailed outline
  3. Create chapter-by-chapter content
  4. Generate metadata (title, summary, tags)
- **Prompt Directory**: `src/application/strategies/outline_chapter/prompts/`

### 2. Stream-of-Consciousness Strategy (`stream-of-consciousness`)
- **Description**: Generates stories in a stream-of-consciousness style with flowing, associative narrative
- **Best for**: Experimental, literary, or introspective stories
- **Process**:
  1. Create minimal outline structure
  2. Generate flowing narrative content
  3. Split into natural sections
  4. Generate poetic metadata
- **Prompt Directory**: `src/application/strategies/stream_of_consciousness/prompts/`

## Configuration

To select a strategy, update your `config.md` file:

```yaml
generation:
  strategy: "outline-chapter"  # or "stream-of-consciousness"
```

## Creating Custom Strategies

To create a new strategy:

1. **Create a new strategy class** that inherits from `StoryStrategy`:

```python
from ..interfaces.story_strategy import StoryStrategy

class MyCustomStrategy(StoryStrategy):
    def __init__(self, model_provider: ModelProvider, config: AppConfig = None):
        super().__init__(model_provider)
        self.config = config
        # Create strategy-specific prompt loader
        from infrastructure.prompts.prompt_loader import PromptLoader
        self.prompt_loader = PromptLoader(prompts_dir=self.get_prompt_directory())
    
    async def generate_outline(self, prompt: str, settings: GenerationSettings) -> Outline:
        # Your outline generation logic
        pass
    
    async def generate_chapters(self, outline: Outline, settings: GenerationSettings) -> List[Chapter]:
        # Your chapter generation logic
        pass
    
    async def generate_story_info(self, outline: Outline, chapters: List[Chapter], settings: GenerationSettings) -> StoryInfo:
        # Your metadata generation logic
        pass
    
    def get_strategy_name(self) -> str:
        return "my-custom-strategy"
    
    def get_strategy_version(self) -> str:
        return "1.0.0"
    
    def get_strategy_description(self) -> str:
        return "Description of what this strategy does"
    
    def get_required_models(self) -> List[str]:
        return ["model1", "model2"]  # List required model names
    
    def get_prompt_directory(self) -> str:
        return "src/application/strategies/my_custom_strategy/prompts"
```

2. **Create prompt directory and files**:

```bash
mkdir -p src/application/strategies/my_custom_strategy/prompts
# Create your prompt files:
# - outline.md
# - content.md
# - metadata.md
# etc.
```

3. **Register the strategy** in `strategy_factory.py`:

```python
from .my_custom_strategy import MyCustomStrategy

def _register_default_strategies(self):
    self.register_strategy("outline-chapter", OutlineChapterStrategy)
    self.register_strategy("stream-of-consciousness", StreamOfConsciousnessStrategy)
    self.register_strategy("my-custom-strategy", MyCustomStrategy)  # Add your strategy
```

4. **Update the factory** to handle your strategy's dependencies:

```python
elif strategy_name == "my-custom-strategy":
    return strategy_class(model_provider, config)  # Adjust based on your needs
```

## Strategy Interface

All strategies must implement the `StoryStrategy` interface:

### Required Methods

- `generate_outline(prompt, settings) -> Outline`: Generate story outline
- `generate_chapters(outline, settings) -> List[Chapter]`: Generate story chapters
- `generate_story_info(outline, chapters, settings) -> StoryInfo`: Generate metadata
- `get_strategy_name() -> str`: Return strategy identifier
- `get_strategy_version() -> str`: Return strategy version
- `get_strategy_description() -> str`: Return human-readable description
- `get_required_models() -> List[str]`: Return list of required model names
- `get_prompt_directory() -> str`: Return prompt directory path

### Dependencies

Strategies receive:
- `model_provider`: Interface for AI model interactions
- `config`: Application configuration (optional)
- `prompt_loader`: For loading external prompts (strategy-specific)

## Prompt Organization

Each strategy has its own prompt directory containing strategy-specific prompts:

### Prompt File Naming
- Use descriptive names: `generate_outline.md`, `create_chapters.md`
- Keep names consistent across strategies when possible
- Use markdown format with clear headers and instructions

### Variable Substitution
Prompts support variable substitution using `{{variable_name}}` syntax:

```markdown
# Example Prompt

Write a story about {{character}} in {{setting}}.

The story should be {{tone}} and include {{elements}}.
```

### Strategy-Specific Prompts
- **Outline-Chapter**: Detailed prompts for each step of the process
- **Stream-of-Consciousness**: Minimal prompts focused on flow and style
- **Custom Strategies**: Design prompts that match your strategy's approach

## Benefits

1. **Modularity**: Each strategy is self-contained with its own prompts
2. **Extensibility**: Easy to add new approaches with dedicated prompt sets
3. **Configuration**: Strategies selectable via config
4. **Maintainability**: Clean separation of concerns
5. **Testability**: Strategies can be tested independently
6. **Plugin Architecture**: New strategies can be added without core changes
7. **Prompt Organization**: Clear structure for managing strategy-specific prompts

## Future Enhancements

Potential strategy ideas:
- **Scene-based strategy**: Generate scene-by-scene instead of chapter-by-chapter
- **Character-driven strategy**: Focus on character development and arcs
- **Plot-driven strategy**: Emphasize plot structure and pacing
- **Dialogue-heavy strategy**: Generate stories with extensive dialogue
- **Poetic strategy**: Generate stories in verse or poetic prose

## Testing Strategies

To test a strategy:

```python
# Test strategy creation
factory = StrategyFactory()
strategy = factory.create_strategy_with_prompts("outline-chapter", model_provider, config)

# Test strategy metadata
print(f"Strategy: {strategy.get_strategy_name()}")
print(f"Version: {strategy.get_strategy_version()}")
print(f"Description: {strategy.get_strategy_description()}")
print(f"Required models: {strategy.get_required_models()}")
print(f"Prompt directory: {strategy.get_prompt_directory()}")
``` 