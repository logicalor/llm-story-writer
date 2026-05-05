---
date: "2026-05-05"
issue: 350
pr: 365
category: agent
targets:
  - ".github/agents-copilot/coder.agent.md"
  - ".github/agents-openrouter/coder.agent.md"
severity: minor
---

## `_extract_json_block` guidance missing layer-boundary exception for `orchestrator.py`

### Finding

Issue #321 added guidance to all coder agents: "prefer `_extract_json_block` from `src/tools/_llm.py` over inline fence-stripping regex." Issue #350 (PR #365) fixed `_coerce_event_list` in `src/presentation/orchestrator.py` using an inline `re.search(r"```(?:json)?\s*([\s\S]*?)```", stripped)` — correctly tolerating leading prose around the fenced block. `orchestrator.py` does not import from `src/tools/`, and adding that dependency would introduce a presentation → tools layer coupling that isn't present elsewhere in the codebase.

### Observation

The existing guidance could cause a future Coder to either (a) add an undesirable `from tools._llm import _extract_json_block` import to `orchestrator.py`, or (b) ignore the guidance without understanding why. Neither outcome is good. The inline regex in `_coerce_event_list` is the correct pattern for presentation-layer code; the guidance should say so.

### Suggested Improvement

Append a layer-boundary exception to the `_extract_json_block` paragraph in `.github/agents-copilot/coder.agent.md` and `.github/agents-openrouter/coder.agent.md`:

> **Exception — presentation layer (`src/presentation/`):** `orchestrator.py` does not import from `src/tools/`; adding that dependency crosses a layer boundary. For presentation-layer helpers that parse LLM output with possible leading/trailing prose, use `re.search(r"```(?:json)?\s*([\s\S]*?)```", text)` to locate the fence anywhere in the string, then `.group(1).strip()` for the content. (Source: issue #350, PR #365.)

### Action Taken

Applied: added the layer-boundary exception sentence to the `_extract_json_block` bullet in both `.github/agents-copilot/coder.agent.md` and `.github/agents-openrouter/coder.agent.md`.
