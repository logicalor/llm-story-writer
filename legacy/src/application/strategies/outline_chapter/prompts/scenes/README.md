# Scene Generation Prompts

This directory contains prompts for the scene-based chapter generation system.

## Overview

The scene generation system breaks down chapters into smaller, more manageable scenes to address LLM coherence issues with long text generation. Instead of generating entire chapters at once, the system:

1. **Parses Chapter Outlines**: Extracts scene definitions from detailed chapter outlines
2. **Generates Individual Scenes**: Creates focused, coherent content for each scene
3. **Combines Scenes**: Merges all scenes into complete chapter content

## File Structure

- `parse_definitions.md` - Parses chapter outlines to identify distinct scenes
- `create_content.md` - Generates content for individual scenes
- `extract_events.md` - Extracts key events from scenes in point form
- `clean_content.md` - Cleans scene content by removing commentary and repetition
- `create_title.md` - Creates titles for individual scenes

## Savepoint Structure

Scenes are saved using the following savepoint pattern:
- `chapter_{num}/scene_{num}` - Scene content
- `chapter_{num}/scene_{num}_summary` - Scene events summary
- `chapter_{num}/scene_{num}_clean` - Cleaned scene content
- `chapter_{num}/scene_{num}_title` - Scene title
- `chapter_{num}/content` - Combined chapter content (all scenes merged)

## Benefits

1. **Better Coherence**: LLMs can maintain focus on smaller text segments
2. **Improved Quality**: Each scene can be optimized for its specific purpose
3. **Easier Debugging**: Individual scenes can be regenerated without affecting the entire chapter
4. **Better Pacing**: Scene-level control allows for more precise narrative pacing
5. **Modular Generation**: Scenes can be generated in parallel or independently

## Workflow

1. Chapter outline is generated with scene definitions
2. For each scene in the outline:
   - Scene content is generated using the scene definition
   - Scene events are extracted in point form and saved as summary
   - Scene content is cleaned to remove commentary and repetition
   - Scene title is generated based on content
   - Both are saved to savepoints
3. All scenes are combined into chapter content
4. Chapter content is saved and used for subsequent processing

## Model Requirements

- `scene_writer` - Primary model for generating scene content
- `logical_model` - Used for parsing scene definitions and generating titles
