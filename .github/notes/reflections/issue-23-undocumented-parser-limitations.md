---
date: "2026-04-16"
issue: 23
pr: 67
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

## YAML parser limitations discovered by review instead of documented at creation

### Finding

During issue #23 (Build Compaction Plugin), the compaction plugin included a YAML frontmatter parser with known edge-case limitations (e.g., multi-line values, complex nested structures). These limitations were not documented in the code or in the feature documentation. The Synthesized Review flagged them, and they were then documented retroactively.

### Observation

When implementing a parser, converter, or any component with known scope constraints, the developer is in the best position to document limitations at creation time — they understand the design trade-offs. Deferring this to review adds a round-trip and risks the limitations being missed entirely if the review doesn't probe deeply enough.

This is the first occurrence of this pattern. It's a documentation discipline issue rather than a code correctness issue — the parser worked correctly within its designed scope.

### Suggested Improvement

No rule change needed for a first occurrence. The current Coder Rule 7 (cleanup before handoff) could theoretically be extended to include "document known limitations," but that broadens Rule 7 beyond its cleanup focus. If this pattern recurs in a future issue, consider adding a brief clause to the Coder's handoff checklist: "document known limitations of new parsers, converters, or format handlers."

### Action Taken

No action needed — first occurrence recorded for pattern tracking. Will revisit if recurrence observed.
