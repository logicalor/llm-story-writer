---
date: "2026-04-23"
issue: 134
pr: 141
category: agent
targets:
  - ".github/agents/documenter.agent.md"
severity: minor
status: active
---

## Documenter documents unimplemented feature behavior as implemented

### Finding

During issue #134 (PR #141, `feat/issue-134-scene-writer-scrub-voice-ops`), the Documenter wrote documentation stating that `scrub_model` is used for the scrub operation while `model` is used for voice analysis — a description of two separate model routing paths. This behavior was not implemented in the production code; only a single `--model` parameter exists on the CLI. The discrepancy was caught by two of three reviewers (GPT + Gemini). The Claude reviewer did not flag it.

The Documenter's Step 3 verification checklist includes rules for output formats, file extensions, directory trees, inventory tables, and code blocks — but no explicit rule about behavioral prose. The Documenter read the issue description (which contained planning language about `scrub_model`) and incorporated it into the documentation as if it were implemented.

### Observation

The issue description and planning materials often contain proposed behaviors that were scoped out, deferred, or reconsidered during implementation. The Documenter has access to both the issue body and the PR diff. When the issue mentions `scrub_model` but the PR diff shows only `--model`, the Documenter should identify the discrepancy and document only what the PR actually implements.

The existing rule "read the Python tool's `cmd_*` functions to verify the exact JSON structure returned" is close in intent but is framed around output format verification, not behavioral claim verification. There is no equivalent rule for routing logic, configuration options, or stated feature capabilities described in prose sections.

This is distinct from the output-format inaccuracy in issue #7 (wrong file extension, wrong return type) — that was a structural fact. This is a **scope creep in documentation**: the Documenter documented the planned scope, not the implemented scope. Both lead to inaccurate docs, but the trigger and the fix are different.

### Suggested Improvement

Add a verification bullet to the Documenter's Step 3 checklist, after the "Scan for TODO stubs" bullet, covering behavioral claims:

```markdown
> - For behavioral descriptions (routing logic, model selection, configuration options, feature flags): read the actual implementation to confirm the described behavior is present in the code. The issue description often contains planned behaviors that were not implemented — do not document them as if they were. Every behavioral claim in the docs must be verifiable in the current codebase by reading the relevant source file.
```

### Action Taken

Applied: added behavioral-description verification bullet to `.github/agents/documenter.agent.md` in the Step 3 checklist.
