---
date: "2026-04-25"
issue: 183
pr: 195
category: instruction
targets:
  - ".github/notes/gotchas.md"
severity: minor
status: archived
---

## ModelConfig.host must be threaded as base_url — model name alone is insufficient

### Finding

PR #195 (issue #183) rewrote `WikiMaintainerAgent.run()` to call `update_wiki_from_chapter()` via
`asyncio.to_thread`. During review, S-C-01 (Critical) found that `model_config.host` was silently
dropped: only `model_config.name` was forwarded through `_prepare_chapter_update` and
`update_wiki_from_chapter`, so the LLM call always resolved to the default endpoint at
`localhost:1234` regardless of the model server configured on the story.

The fix threaded `base_url` through every layer:
- `_llm.generate_text` / `_chat_completion` — now accept `base_url: str | None = None`
- `_prepare_chapter_update` / `update_wiki_from_chapter` — now accept and forward `base_url`
- `wiki_maintainer.py` — derives `base_url = f"http://{model_config.host}/v1" if model_config.host else None`

### Observation

This is a recurrent pattern when new programmatic APIs are extracted from tool scripts. The tool
script's original `argparse`-driven code read both `--model` and the base URL from config; when
a programmatic wrapper is added, it is easy to forward only the model name and overlook the
endpoint derivation. The LLM call silently succeeds (local default server exists) but targets
the wrong endpoint in any multi-endpoint deployment.

### Suggested Improvement

Add a gotcha entry to `.github/notes/gotchas.md` documenting the derivation pattern and the
silent failure mode when `base_url` is omitted.

### Action Taken

Applied: Added gotcha #029 to `.github/notes/gotchas.md` under the "Python Patterns" section.
