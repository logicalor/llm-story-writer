---
date: "2026-04-18"
issue: 103
pr: 105
category: instruction
targets:
  - ".github/notes/gotchas.md"
severity: minor
status: active
---

## Gemini false positives: sys.path.insert convention and fabricated consolidation target

### Finding

During PR #105 (two-line null guard in `OutlineGenerator._index_story_analysis_chunk`), Gemini
produced two false positive findings that were correctly dismissed by the Synthesizing Reviewer:

**FP-1 — sys.path.insert flagged as anti-pattern:** Gemini flagged
`sys.path.insert(0, str(Path(__file__).parent.parent))` in the new regression test file, claiming
pytest already auto-discovers `src/` via pyproject.toml configuration. The premise is factually
incorrect: the project's `pyproject.toml` does NOT include `pythonpath = ["src"]` under
`[tool.pytest.ini_options]`. Manual path insertion is required and is an established convention
confirmed across 7+ test files in the codebase (verified by Claude during review).

**FP-2 — consolidation target fabricated:** Gemini suggested consolidating the new focused test
file into `test_outline_generator.py`. That file does not exist — Gemini hallucinated the
destination path.

### Observation

Both false positives were correctly identified and dismissed by the Synthesizing Reviewer
(Phase D triage). The pipeline performed as designed at every stage: three independent reviews,
synthesis, false-positive filtering, unanimous merge approval with zero blocking findings.

The `sys.path.insert` pattern has been flagged before (PR #43, M-S-02, resolved as a
suggestion). Its status as an established, necessary convention is not documented in the shared
knowledge base, making it a recurring source of reviewer confusion. Adding a gotcha entry gives
future reviewers a facts-on-the-ground reference embedded in the `conventions` ChromaDB
collection — making it available contextually during the next review that touches a tool test
file.

The fabricated consolidation target (FP-2) is a variant of the hallucination pattern documented
in issues #19, #22, and #69. No structural change needed — the Synthesizing Reviewer
architecture handles this class of error reliably.

### Suggested Improvement

Add gotcha entry #007 to `.github/notes/gotchas.md` documenting that `sys.path.insert` in test
files for `src/tools/` scripts is an established, necessary convention — not an anti-pattern —
because `pyproject.toml` does not configure `pythonpath = ["src"]`.

### Action Taken

Applied: added gotcha `#007 — sys.path.insert in tool test files` to `.github/notes/gotchas.md`.
Embedded this reflection into the `reflections` ChromaDB collection. Stale active-directory
duplicates for issues #26, #90, and #100 (×3) confirmed archived — active copies pending
deletion (see cleanup note in output).
