# Chapter Prompts

This directory contains all prompts related to chapter generation and management in the outline-chapter strategy.

## Prompt Files

### Core Chapter Operations

- **`create_content.md`** - Generates the actual chapter content from outline
- **`create_title.md`** - Generates a title for a chapter
- **`create_list.md`** - Generates a list of chapters
- **`create_list_iterative.md`** - Generates iterative chapter list with detailed synopses

### Chapter Outline Management

- **`outline.md`** - Main chapter outline generation prompt

## Workflow

1. **Chapter Planning**: Use `create_list.md` to plan chapter structure
2. **Outline Generation**: Use `outline.md` to create detailed chapter outlines
3. **Content Creation**: Use `create_content.md` to generate chapter content
4. **Title Generation**: Use `create_title.md` to create chapter titles

## Usage

These prompts are used by the `ChapterGenerator` class to:
- Generate chapter outlines from synopses
- Create chapter content from outlines
- Generate chapter titles and metadata
- Manage chapter structure and flow

## Naming Convention

All prompts use concise, descriptive names that clearly indicate their function:
- `create` - Creates new content
- `outline` - Manages chapter outlines
