---
date: "2026-05-03"
issue: 321
pr: 333
category: agent
targets:
  - ".github/agents-copilot/coder.agent.md"
  - ".github/agents-openrouter/coder.agent.md"
severity: minor
---

## Inline fenced-block regex in orchestrator duplicates `_extract_json_block` from `_llm.py`

### Finding

PR #333 (issue #321, ADR 011 Task 6) introduced an inline
`re.search(r"```json\s*(.*?)\s*```", enrichment_suggestions, re.DOTALL)` in
`_continue_pipeline` (~line 1048 of `orchestrator.py`) to extract JSON from the
`enrichment_suggestions` field before parsing. The codebase already provides
`_extract_json_block(text)` in `src/tools/_llm.py`, which strips `` ```json `` or plain
`` ``` `` fences and extracts the first JSON object or array — functionally equivalent
for this input.

### Observation

The inline regex handles only the `` ```json … ``` `` variant. `_extract_json_block` handles
both `` ```json `` and plain `` ``` `` and also strips surrounding prose. If the LLM emits
the fence without the `json` language specifier, the inline regex falls back to the raw
fenced string (which may still include fences), while `_extract_json_block` would strip them.

More broadly: each new inline fence-stripping pattern is a future divergence point. When the
shared helper is later improved (e.g. to handle single-backtick variants or `<JSON>` tags),
inline copies do not benefit. The `_extract_json_block` + `_strip_markdown_fences` helpers
exist precisely to centralise this logic.

### Suggested Improvement

Add a bullet to the "Code Patterns" section of both Coder agent files immediately after the
existing LLM JSON parsing guards, stating that when extracting JSON from an LLM response
string that may contain markdown fences, Coders should prefer `_extract_json_block(text)`
from `src/tools/_llm.py` over inline regex, then call `json.loads()` on the result.

### Action Taken

Applied: added bullet to both `coder.agent.md` files under "LLM JSON structured response
parsing guards" section.
