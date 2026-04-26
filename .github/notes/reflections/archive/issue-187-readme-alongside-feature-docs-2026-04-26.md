---
date: "2026-04-26"
issue: 187
pr: 200
category: agent
targets:
  - ".github/agents/documenter.agent.md"
severity: minor
status: archived
---

## README.md is the most user-visible surface — update it alongside docs/ for keybinding and UI changes

### Finding

During issue #187/PR #200, the Documenter updated `docs/features/` with revised keybinding information but missed `README.md` at the repository root. README.md is the first file prospective users and contributors read — it is higher-traffic than any individual feature doc. Stale keybindings or interface descriptions in README.md are more damaging than the equivalent stale entry in a feature doc.

### Observation

README.md is not inside `docs/` and is not part of the standard documenter sweep (`docs/README.md` index maintenance does not cover the repo-root `README.md`). The Documenter's rule set explicitly covers `docs/` contents but does not name the repo-root README as a mandatory co-update surface. Any UI-visible change (keybindings, CLI flags, subcommands, workflow steps described in prose) that touches `docs/features/` should also be checked against `README.md`.

### Suggested Improvement

Add a rule to `documenter.agent.md`'s **Workflow → Step 2 (Determine Documentation Needs)** table: when the change type includes UI-visible updates (keybindings, CLI flags, subcommand additions/removals, interface descriptions), include `README.md` (repo root) in the update scope alongside the relevant `docs/features/` file.

### Action Taken

Applied: Added a row to the documentation-needs table in `documenter.agent.md` Step 2 for UI-visible changes (keybindings, CLI flags, subcommands) requiring README.md co-update.
