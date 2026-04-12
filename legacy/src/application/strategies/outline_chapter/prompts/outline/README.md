# Outline Prompts

This directory contains all prompts related to story outline generation and management in the outline-chapter strategy.

## Prompt Files

### Core Outline Operations

- **`create.md`** - Generates the initial story outline
- **`create_skeleton.md`** - Creates a basic outline skeleton
- **`create_chunk.md`** - Generates outline chunks for long stories
- **`create_elements.md`** - Generates story elements and components
- **`create_title.md`** - Generates the story title
- **`create_summary.md`** - Creates story summary
- **`create_tags.md`** - Generates story tags and metadata

### Outline Analysis & Processing

- **`analyze_enrichment.md`** - Analyzes story for enrichment opportunities
- **`analyze_continuity.md`** - Analyzes chunk continuity and flow
- **`strip_elements.md`** - Strips and processes story elements

## Workflow

1. **Story Elements**: Use `create_elements.md` to identify core story components
2. **Outline Creation**: Use `create.md` to generate the main story outline
3. **Structure Planning**: Use `create_skeleton.md` for basic outline structure
4. **Chunked Generation**: Use `create_chunk.md` for long stories (when chunked generation is enabled)
5. **Metadata Generation**: Use `create_title.md`, `create_summary.md`, and `create_tags.md`
6. **Quality Analysis**: Use `analyze_enrichment.md` and `analyze_continuity.md` for refinement

## Usage

These prompts are used by the `OutlineGenerator` class to:
- Generate initial story outlines from prompts
- Create story structure and flow
- Generate story metadata and summaries
- Analyze and improve outline quality
- Process story elements and components

## Naming Convention

All prompts use concise, descriptive names that clearly indicate their function:
- `create` - Creates new content
- `analyze` - Analyzes existing content
- `strip` - Processes and extracts content
