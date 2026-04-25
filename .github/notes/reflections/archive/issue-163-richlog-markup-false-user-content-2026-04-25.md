---
date: "2026-04-25"
issue: 163
pr: 174
category: instruction
targets:
  - ".github/notes/gotchas.md"
severity: minor
status: archived
---

## RichLog `markup=True` (default) corrupts display of LLM token output

### Finding

`RichLog` in Textual defaults to `markup=True`, which interprets Rich markup syntax
(`[bold]`, `[red]`, `[link=…]`) in every string written to it. LLM-generated content
routinely contains square-bracket sequences that Rich parses as markup — even literal
`[1]`, `[citation]`, or half-formed tags. When Rich encounters an unrecognised or
unclosed tag it raises a `MarkupError` or silently drops content, corrupting the display.

The fix is to pass `markup=False` when constructing any `RichLog` that receives
user-generated or LLM-generated content:

```python
# Wrong — default markup=True corrupts LLM tokens with [] content:
log = RichLog()

# Right — markup=False treats all content as plain text:
log = RichLog(markup=False)
```

This was discovered in review when the token streaming panel displayed garbled output
during a test story run that contained Markdown citation brackets.

### Observation

The bug is invisible during unit tests because mock token streams rarely contain characters
that Rich parses as markup. It only manifests in integration or end-to-end runs with real
LLM output. Reviewers who do not test the TUI with realistic LLM content will miss it.

The wider principle: **never set `markup=True` on any display widget that renders
user-generated or model-generated content** — the application has no control over whether
that content contains Rich markup syntax.

### Suggested Improvement

Add gotcha #024 to `.github/notes/gotchas.md` under a new "UI / Textual" section.

### Action Taken

Applied: Added gotcha #024 to `.github/notes/gotchas.md`.
