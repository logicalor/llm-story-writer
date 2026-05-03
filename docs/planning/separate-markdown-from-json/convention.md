# Markdown Pointer Storage Convention

> Defines the pointer-based markdown storage convention introduced by ADR 011.

## Overview

JSON fields that contain markdown content are stored as pointer objects instead of inline strings. The JSON value becomes `{ "$ref": "..." }`, and the markdown body lives in a sibling `.md` file on disk. This keeps JSON for structured metadata, keeps markdown editable as markdown, and gives the pipeline stable file paths for follow-on indexing and migration work.

## What Counts As Markdown Content

A field counts as markdown content if any of these rules match:

1. It contains `\n\n`.
2. It contains a markdown heading matching `^#{1,6} `.
3. It contains a fenced code block marker `` ``` ``.
4. It exceeds 500 characters of free text.

When a field matches any rule, persist the body to a `.md` file and store a pointer in JSON instead of the raw string.

## Pointer Shape

Pointer objects use one shape only:

```json
{ "$ref": "relative/path/to/file.md" }
```

Paths are always relative to the story root. The `$ref` key is the single recognised marker. This follows familiar JSON Schema and OpenAPI vocabulary.

## Rule B: No JSON Inside Markdown Fenced Blocks

Structured payloads stay structured. If a value is JSON, persist it as JSON in a JSON file or JSON sub-document. Do not store structured data as a `` ```json `` string inside another JSON value.

This rule prevents double-encoded and triple-encoded payloads that are hard to diff, validate, and round-trip safely.

## Storage Path Conventions

Suggested path patterns:

- Character sheets: `characters/<slug>/sheet.md`, `characters/<slug>/chunks/<key>.md`
- Setting sheets: `settings/<slug>/sheet.md`, `settings/<slug>/chunks/<key>.md`
- Chapter recaps: `chapters/chapter_<N>/recap.md`
- Story prompt: `prompt.md`
- Outline chapter summaries: `outline/chapter_<N>_summary.md`
- Outline story foundation fields: `outline/base_context.md`, `outline/story_elements.md`

These paths are conventions, not arbitrary examples. Writers should keep file locations stable so downstream readers, migrations, and ChromaDB source-sync can rely on predictable on-disk paths.

## Helper API

The persistence helpers live in `src/tools/_persist.py`.

- `persist_markdown(story_root, relative_path, body)` writes the markdown file atomically and returns the pointer dict.
- `read_markdown_ref(story_root, ref)` resolves either a pointer dict or a legacy inline string and returns the markdown body.

Reference signatures:

```python
persist_markdown(story_root, relative_path, body) -> {"$ref": relative_path}
read_markdown_ref(story_root, ref) -> str
```

## Backward Compatibility

`read_markdown_ref` accepts both legacy plain strings and new pointer dicts. Read sites can switch to the helper immediately without breaking stories that still store inline markdown during the migration window.

## Concrete Example

Before:

```json
{
  "sheet": "# Yara Osei\n\n## Background\n\nYara was born..."
}
```

After:

```json
{
  "sheet": {"$ref": "characters/yara-osei/sheet.md"}
}
```

The markdown body then lives in `characters/yara-osei/sheet.md` relative to the story root.

## JSON Schema

`src/application/schemas/markdown_ref.json` validates the pointer shape. The schema requires a single `$ref` string and rejects additional properties.