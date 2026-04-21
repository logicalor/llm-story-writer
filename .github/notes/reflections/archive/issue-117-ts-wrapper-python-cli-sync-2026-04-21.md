---
date: "2026-04-21"
issue: 117
pr: 118
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## Python CLI changes must propagate to TypeScript wrapper — TS layer invisible to Python-only reviews

### Finding

During PR #118, the Coder extended `critique_runner.py` with two new argparse flags (`--mode` and `--criterion-floor`) but did not update the corresponding TypeScript wrapper (`critique-runner.ts`) to expose them in the Zod schema or `args` builder. This caused the new chapter critique workflow to fail silently: the orchestrator passes `mode: "chapter"` to the tool, the wrapper strips it (unknown Zod field), and Python falls back to the `"outline"` default — producing wrong output with no error.

Critically, Claude's review of the PR missed this entirely. Claude reviewed the Python layer and agent instructions thoroughly but did not verify whether the TypeScript wrapper matched the updated Python CLI contract. GPT and Gemini both independently caught the gap as a Critical finding. This confirms the gap is non-obvious and models can be blind to the TS layer when reviewing Python-heavy PRs.

### Observation

The existing Rule 10 verification checklist covers reading the TS wrapper to verify operation names, Zod parameter types, and parameter key names. However, this applies in the direction of "what does the wrapper expose?" — verifying documentation/agent files are accurate about the tool interface. It does not explicitly cover the inverse direction: "did I add new Python CLI parameters that also need TS wrapper entries?"

The Implementation Order section lists Python tools (step 2) before TypeScript wrappers (step 3), which is correct for new tool creation. But for modifications to existing tools, the two layers must change atomically — a Python CLI change without a corresponding TS wrapper change is an incomplete implementation.

This is the second related pattern after issue #113 (z.string vs z.object type representation) and issue #115 (parameter key name vs Zod field name). Together they form a cluster: the TS/Python boundary produces subtle failures invisible to lint and Python tests.

### Suggested Improvement

Add a paragraph to the Implementation Order section of coder.agent.md, after "This ensures each layer's dependencies exist before it references them," clarifying that modifying an existing Python tool's CLI requires an atomic Python+TS wrapper update.

### Action Taken

Applied: added "When modifying an existing Python tool's CLI" guidance block to the Implementation Order section of `.github/agents/coder.agent.md`.
