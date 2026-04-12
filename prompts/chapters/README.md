# Chapter Prompts

This directory contains all prompts related to chapter generation and management in the outline-chapter strategy.

## Prompt Files

### Core Chapter Operations

- **`create_content.md`** - Generates the actual chapter content from outline
- **`create_title.md`** - Generates a title for a chapter
- **`get_outline.md`** - Retrieves chapter outline from synopsis
- **`create_list.md`** - Generates a list of chapters
- **`create_list_iterative.md`** - Generates iterative chapter list with detailed synopses

### Chapter Outline Management

- **`outline.md`** - Main chapter outline generation prompt
- **`outline_core.md`** - Core chapter outline functionality
- **`outline_improved.md`** - Enhanced chapter outline generation
- **`outline_validator.md`** - Validates chapter outline quality
- **`outline_formatter.md`** - Formats chapter outline consistently
- **`outline_disambiguator.md`** - Resolves ambiguities in chapter outlines
- **`outline_cleanup.md`** - Cleans up chapter outline formatting

## Workflow

1. **Chapter Planning**: Use `create_list.md` to plan chapter structure
2. **Outline Generation**: Use `outline.md` to create detailed chapter outlines
3. **Content Creation**: Use `create_content.md` to generate chapter content
4. **Title Generation**: Use `create_title.md` to create chapter titles
5. **Quality Control**: Use `outline_validator.md` and `outline_formatter.md` for refinement

## Usage

These prompts are used by the `ChapterGenerator` class to:
- Generate chapter outlines from synopses
- Create chapter content from outlines
- Generate chapter titles and metadata
- Validate and format chapter outlines
- Manage chapter structure and flow

## Naming Convention

All prompts use concise, descriptive names that clearly indicate their function:
- `create` - Creates new content
- `outline` - Manages chapter outlines
- `get` - Retrieves existing content
- `validator` - Validates content quality
- `formatter` - Formats content consistently
