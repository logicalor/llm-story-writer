---
date: "2026-04-16"
issue: 23
pr: 67
category: agent
targets:
  - ".github/agents/coder.agent.md"
severity: major
status: active
---

## Coder missed plugin registration in opencode.json — framework discovery not verified

### Finding

During issue #23 (Build Compaction Plugin), the Coder implemented the compaction plugin file (`.opencode/plugins/story-compaction.ts`) but did not register it in `opencode.json`. The Synthesized Review caught this as a critical finding — without registration, OpenCode would never load the plugin.

The Coder created the artifact correctly but did not verify how OpenCode discovers and loads plugins. No existing Coder rule covers framework registration/discovery verification.

### Observation

This is a distinct defect class from schema fabrication (issue #19, parameter names) and semantic correctness (issue #10, wiring bugs). The pattern is: implementing a framework artifact without verifying the framework's discovery mechanism. The file was syntactically and semantically correct in isolation, but not integrated into the host system.

Analogous real-world patterns:
- Creating a Django app without adding it to `INSTALLED_APPS`
- Writing a pytest plugin without an entry point
- Creating an OpenCode tool without a `.opencode/tools/*.ts` wrapper

This is the first occurrence in this project. If it recurs, it would warrant a dedicated Coder rule. The related issue #19 proposal (verify tool parameter schemas) is pending approval — these could be combined into a broader "framework integration verification" rule.

### Suggested Improvement

Add a new Coder rule (or extend the pending issue #19 proposal) requiring the Coder to verify framework registration/discovery when creating new artifact types:

> **Rule 10: Framework integration verification.** When creating a new framework artifact (plugin, tool, agent, command, skill), verify:
> a) **Registration/discovery** — how the framework finds and loads the artifact. Check config files (`opencode.json`, `package.json`, manifests) and ensure the new artifact is registered.
> b) **Schema conformance** — parameter names, types, and required fields match the actual framework schemas (see issue #19).
>
> Grep the project for existing examples of the same artifact type and replicate the integration pattern.

This combines the issue #19 schema verification with the issue #23 registration verification into a single rule covering framework integration completeness.

### Action Taken

Proposed for approval — new Coder Rule 10 (Framework Integration Verification).
