# Inline Markdown Lint Gate

This lint gate prevents large markdown bodies from being stored inline inside story JSON files. The repository now treats markdown-heavy content as external files referenced by `{"$ref": "..."}` pointers, which keeps JSON state small, diffable, and easier to migrate safely.

The lint scans every JSON file under `stories/` and recursively inspects string values. For non-allowlisted field names, it reports a violation when a string looks like embedded markdown or other bulky prose. The current checks flag paragraph breaks, markdown headings, fenced code markers, and any string longer than 500 characters.

Run it locally with:

```bash
python3 scripts/lint_no_inline_markdown.py
python3 scripts/lint_no_inline_markdown.py --stories-dir /path/to/stories
```

If a field should remain exempt, add its field name to `ALLOWLIST_FIELDS` near the top of `scripts/lint_no_inline_markdown.py`. Keep that allow-list conservative. Exempt fields by name only when short inline text is expected across all uses of that field.

If the lint reports legacy inline markdown, migrate the story data first:

```bash
python3 src/tools/migrate_inline_markdown.py --name my-story
python3 src/tools/migrate_inline_markdown.py --all
python3 src/tools/migrate_inline_markdown.py --name my-story --dry-run
```

The migration writes extracted markdown or JSON files beside the story data, updates JSON fields to pointer dictionaries, and creates `.premigrate` backups before changing any JSON file.