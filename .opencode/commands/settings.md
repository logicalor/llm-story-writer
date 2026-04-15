---
description: View or modify generation settings
---

Current configuration:
@config.md

If no arguments were provided (empty "$1"), display all current settings from the YAML frontmatter above in a formatted table grouped by section (models, generation, translation, infrastructure).

If a setting key was provided ("$1") without a new value (empty "$2"), show just that setting's current value.

If both a setting key ("$1") and new value ("$2") were provided, modify that setting in `config.md`'s YAML frontmatter:
- Edit only the specific key-value pair
- Preserve all other YAML formatting, comments, and structure
- Be careful with YAML indentation — incorrect indentation will break the config
- Confirm the change was made and show the old and new values
