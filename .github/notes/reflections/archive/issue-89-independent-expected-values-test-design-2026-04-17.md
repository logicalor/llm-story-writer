---
date: "2026-04-17"
issue: 89
pr: 96
category: agent
targets:
  - ".github/agents/test-writer.agent.md"
severity: minor
status: archived
---

## Reviewers raised false positive on intentional duplicate constant — independent expected value pinning

### Finding

Issue #89 (PR #96) strengthened a chunk count assertion in an integration test and removed an unused `MAX_CONTEXT_TOKENS` constant. The test defines `ANALYSIS_CHUNK_TYPES` locally — a tuple that mirrors `CHUNK_TYPES` in `outline_generator.py` exactly. During the synthesized review, the majority suggested importing the production constant rather than duplicating it, classifying the duplication as a DRY violation.

The suggestion was correctly rejected: the duplication is intentional test design. Pinning the expected value independently means the test fails if the production constant changes silently — which is the desired behaviour. Importing the production constant would make the test pass trivially on any change, defeating the assertion's purpose.

The Documenter step was correctly skipped (test-only PR with no production code changes) — this is consistent with existing issue #69 guidance.

### Observation

The reviewers did not recognise independent expected value pinning as a deliberate testing pattern. This is a well-established test design practice: expected values in tests should be authored independently of the production constants they verify, so that production changes require the test to be explicitly updated. Importing the production constant creates a tautological assertion.

The false positive arises because the duplicate constant *looks* like an accidental oversight — DRY violation detectors flag it without understanding the intent. Adding a comment (`# Independent expected value — intentional test design`) or having the Test Writer include this pattern in a named guidance block would prevent future false positives.

This is the same category of issue as the "Collection assertions" guidance (issue #88) and "CLI validation assertions" guidance (issue #94) — pattern knowledge that the Test Writer should apply consistently.

### Suggested Improvement

Add an "Independent expected values" named block to the Test Writer agent's **Write Tests** section, after the existing "CLI validation assertions" block:

```markdown
**Independent expected values:** When asserting against known list, set, or constant values, define those values directly in the test rather than importing them from production code. This pins the expected value independently — if a production constant changes silently, the test fails, which is the correct behaviour. Importing the production constant would make the test pass trivially on any change, defeating its purpose. Add a comment such as `# Independent expected value — intentional test design` to clarify this is not accidental duplication.
```

### Action Taken

Applied: added "Independent expected values" block to `.github/agents/test-writer.agent.md` after the "CLI validation assertions" block.
