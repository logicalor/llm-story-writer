---
date: "2026-04-22"
issue: 121
pr: 128
category: agent
targets:
  - ".github/agents/_shared/review-checklist.md"
severity: minor
status: archived
---

## Tool parameters accepted by TS wrapper but silently ignored by Python backend

### Finding

During PR #128 (feat: final-editor and prose-scrubber subagents), `final-editor.md` passed `chapterNum: N` to `rag-query` with `operation: "query"`. The TypeScript wrapper accepts `chapterNum` via its Zod schema. However, the Python backend (`src/tools/rag_query.py`) never reads `--chapter-num` for query operations — the parameter is accepted by Zod but never forwarded to, or consumed by, the Python CLI. The result is that a parameter the agent's author believed would constrain query scope had no effect; the RAG query ran without the intended filter.

Defect code: **[U-W-01]** — classified as a unique warning. The silently-ignored parameter does not produce an error; it produces incorrect (un-scoped) results with no diagnostic output.

### Observation

The existing `Tool call contracts` Phase 2 checklist item (a)–(c) directs reviewers to verify operation names, Zod key names, and omitted-parameter defaults. It does not direct reviewers to verify the inverse: that parameters supplied to the tool are actually consumed and produce the intended effect.

The failure mode here differs from key-name mismatches and operation-name errors:
- The tool invocation is structurally valid (Zod accepts it)
- The operation runs without error
- The return value is plausibly correct in shape but wrong in scope

This class of defect — "accepted but ignored parameter" — produces incorrect agent behaviour that is invisible to lint, type checks, and quick functional tests. It is only caught by reading both the TS wrapper (to see what Zod accepts) AND the Python source (to verify the argument is added to `argparse` and actually used in the relevant operation branch).

Without an explicit checklist prompt to verify consumption (not just schema acceptance), reviewers will see a valid Zod schema and valid operation name and approve the invocation.

### Suggested Improvement

**Change 1 — review-checklist.md Phase 2 Agent Instructions item (e):**

Extend the `Tool call contracts` item with a fifth verification point (after the new item (d) from issue-121-ts-optional-python-conditional-required):

> (e) any parameter passed to the tool is verified to be consumed by the Python backend for the active operation — TS wrappers may accept parameters via Zod that the Python CLI never reads in certain operation branches; passing an accepted-but-ignored parameter produces silently incorrect results; verify by checking `argparse.add_argument` declarations and the operation dispatch branch in `src/tools/*.py`.

### Action Taken

Applied: added item (e) to the Tool call contracts checklist entry in `.github/agents/_shared/review-checklist.md`.
