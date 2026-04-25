---
date: "2026-04-25"
issue: 182
pr: 194
category: agent
targets:
  - ".github/agents/orchestrator-v3.agent.md"
  - ".github/agents/synthesizing-reviewer.agent.md"
severity: minor
status: archived
---

## Annotation noise in review package diff causes reviewer false positive

### Finding

During PR #194, the Orchestrator included an inline annotation comment `# VERIFY: should be 'characters'`
inside a diff snippet it passed to all three reviewer agents. Gemini read this annotation as a genuine
code comment and reported a Critical bug: "the variable is incorrectly labelled 'characters'". The
annotation was a working note added by the Orchestrator during diff assembly — not production code — but
Gemini had no way to distinguish it from real source content.

The Synthesizing Reviewer correctly identified the false positive and excluded it from consensus, but
it cost analysis time and required explicit divergence documentation.

### Observation

Any temporary annotation the Orchestrator writes into the diff excerpt (`# VERIFY:`, `# TODO:`,
`# CHECK:`, `# NOTE:`) before pasting into the review package is indistinguishable from real source
code comments at the model level. Reviewers treat the diff as a verbatim snapshot of the codebase.
This is a systematic false-positive injection vector: one annotation per review ≈ one false positive
per review cycle.

The Phase A instruction already warns against transcription errors ("never reconstruct from memory")
but does not address deliberate annotation insertion by the Orchestrator itself.

### Suggested Improvement

1. Add a prohibition in Phase A of Orchestrator Step 7 immediately after the review package assembly
   template: "Do NOT add inline annotations, `# VERIFY:`, `# TODO:`, `# NOTE:`, or any other comments
   into code blocks or diff excerpts in the review package. The package must be a verbatim copy of
   source and diff output only."

2. Add a false-positive filter bullet to the Synthesizing Reviewer Step 2 for annotation artifacts.

### Action Taken

Applied:
- Added annotation prohibition note to Orchestrator Step 7 Phase A review package assembly block.
- Added "Annotation artifact filter" to Synthesizing Reviewer Step 2 false-positive filters.
