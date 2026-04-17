---
date: "2026-04-17"
issue: 27
pr: 87
category: agent
targets:
  - ".github/agents/orchestrator-v3.agent.md"
severity: minor
status: archived
---

## Review package must be assembled from `read_file`, never from memory

### Finding

During issue #27 (Task 25: End-to-End Integration Test with Wiki), the Orchestrator assembled the review package for the reviewer sub-agents with a transcription error: `"planned"` was accidentally omitted between `"--confidence"` and `"--first-appearance"` in the CLI argument list for a tool call. The reviewer (Claude) correctly flagged this as a Critical bug (C-01: missing required argument), but it was a false positive — the actual source file was correct; only the review package transcription was wrong. Time was spent investigating and re-reading the file before the false positive was confirmed.

### Observation

The review package's Phase A instructions say "For each changed file in the list, read the entire file." This implies using `read_file`, but it does not explicitly forbid reconstructing content from memory, scroll output, or earlier context. The Orchestrator made a transcription error because it filled in file content from context rather than reading it verbatim.

This is particularly harmful because:

1. It injects false positives into the review — reviewers see bugs that don't exist in the code.
2. It wastes investigation time triaging the false positive.
3. The transcription error is invisible to reviewers — they have no way to detect that the package doesn't match the actual file.

The fix is simple: always use `read_file` for file contents in the review package, period. Never reconstruct from memory after a file has been read earlier in the session — re-read it immediately before assembling.

### Suggested Improvement

Add an explicit warning to Phase A, Step 5:

> For each changed file in the list, **use `read_file` to copy the content verbatim** — never reconstruct from memory, scroll output, or earlier context. Transcription errors silently inject false-positive findings into the review.

### Action Taken

Applied: added verbatim `read_file` warning to Orchestrator Phase A Step 5.
