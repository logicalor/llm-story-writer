# Scene Generation Implementation

## Overview

This document summarizes the implementation of scene-based chapter generation to address LLM coherence issues with long text generation.

## Problem Addressed

LLMs struggle to maintain coherence when generating large amounts of text (like entire chapters). This leads to:
- Loss of narrative focus
- Inconsistent character voices
- Plot inconsistencies
- Reduced overall quality

## Solution Implemented

### 1. Scene Entity
- Added `Scene` class to `src/domain/entities/story.py`
- Each scene has: number, title, content, outline, word count, and metadata
- Scenes are contained within chapters

### 2. Updated Chapter Entity
- Modified `Chapter` class to include a `scenes` field
- Updated serialization/deserialization methods to handle scenes
- Chapters now combine multiple scenes instead of generating content directly

### 3. Scene Generator Service
- Created `src/application/strategies/outline_chapter/scene_generator.py`
- Handles parsing chapter outlines for scene definitions
- Generates individual scene content and titles
- Manages scene savepoints

### 4. Modified Chapter Generation Workflow
- Updated `ChapterGenerator` to use scene generation instead of direct content generation
- Chapter generation now:
  1. Generates chapter outline with scene definitions
  2. Generates individual scenes from the outline
  3. Combines scenes into chapter content
  4. Saves both individual scenes and combined content

### 5. New Prompt System
- `parse_definitions.md` - Extracts scene definitions from chapter outlines
- `create_content.md` - Generates focused scene content
- `create_title.md` - Creates scene titles
- Updated chapter outline prompt to explicitly request scene breakdowns

## Savepoint Structure

The new savepoint structure follows the pattern:
```
chapter_{num}/
├── base_outline          # Chapter outline with scene definitions
├── scene_1               # Scene 1 content
├── scene_1_title         # Scene 1 title
├── scene_2               # Scene 2 content
├── scene_2_title         # Scene 2 title
├── content               # Combined chapter content
└── recap                 # Chapter recap
```

## Benefits

1. **Improved Coherence**: LLMs can focus on smaller, manageable text segments
2. **Better Quality**: Each scene can be optimized for its specific narrative purpose
3. **Easier Debugging**: Individual scenes can be regenerated without affecting the entire chapter
4. **Modular Generation**: Scenes can be generated independently or in parallel
5. **Better Pacing**: Scene-level control allows for more precise narrative pacing
6. **Consistent Structure**: Each scene follows a clear, focused format

## Configuration Changes

- Added `scene_writer` model to required models list
- Removed `chapter_stage1_writer` model requirement
- Updated system to handle scene-based savepoints

## Usage

The scene generation system is automatically used when generating chapters. The workflow is:

1. **Outline Generation**: Chapter outlines are created with explicit scene definitions
2. **Scene Generation**: Each scene is generated individually using the scene definition
3. **Content Combination**: All scenes are merged into complete chapter content
4. **Savepoint Management**: Both individual scenes and combined content are saved

## Future Enhancements

Potential improvements could include:
- Scene-level character and setting extraction
- Scene-specific pacing controls
- Parallel scene generation for improved performance
- Scene-level quality validation and regeneration
- Scene dependency management for complex narratives
