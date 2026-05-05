# Merge Wiki Page Patch

You are updating an existing wiki page using a newly extracted candidate.

<EXISTING_PAGE>
{existing_page_body}
</EXISTING_PAGE>

<NEW_CANDIDATE>
{new_candidate}
</NEW_CANDIDATE>

## Task

Return a JSON patch describing only the changes needed to merge the new candidate into the existing page.

## Output schema

```json
{
  "frontmatter_delta": {"key": "new_value"},
  "body_append": "Text to append to the end of the page body.",
  "body_sections_replace": [
    {"heading": "## Section Name", "new_content": "Replacement section body text."}
  ],
  "aliases_add": ["alias1"],
  "no_change": false
}
```

## Rules

- Emit a structured patch only. Do not rewrite or reproduce the full page.
- Never replace the whole page body. Use only `frontmatter_delta`, `body_append`, `body_sections_replace`, and `aliases_add`.
- Omit fields that do not need changes.
- If no update is needed, return exactly `{"no_change": true}`.
- Keep existing content unless the new candidate clearly extends it or corrects it.
- Use `body_append` for net-new facts that belong at the end of the current body.
- Use `body_sections_replace` only when an existing section should be refreshed in place. Set `heading` to the exact Markdown heading text to replace.
- Use `aliases_add` only for genuinely new aliases not already present.
- Use `frontmatter_delta` only for specific fields that should be added or changed.
- Return valid JSON object only. No markdown fences. No commentary.