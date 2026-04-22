---
date: "2026-04-22"
issue: 123
pr: 129
category: agent
targets:
  - ".github/agents/_shared/code-review-process.md"
  - ".github/agents/coder.agent.md"
severity: minor
status: archived
---

<!-- Archived. Full note in archive/issue-123-opencode-json-registry-gap-2026-04-22.md -->

### Finding

During PR #129 (feat: add chapter-outline-expander subagent and chapter handoff artifact), the new `chapter-outline-expander` agent was not registered in `opencode.json` — absent from both the `agent:` block and `story-orchestrator`'s `permission.task` allow-list, which uses a deny-by-default (`"": "deny"`) policy. This would have caused Phase 7a to fail immediately at runtime with no informative error message. Only Gemini caught it by inspecting `opencode.json` directly. Claude and GPT both declared "9 files reviewed" but neither model read the config file, creating a coverage gap that allowed a verified Critical finding to escape two of three review models.

Additionally, the Coder agent's Rule 10 already specifies "Check config files (opencode.json, package.json, manifests) and ensure the new artifact is registered" — but this was insufficient to prevent the omission. The rule does not distinguish the two-step nature of agent registration: (1) adding the agent to the `agent:` block, and (2) adding it to the `permission.task` allow-list of every orchestrator using a deny-by-default policy.

### Observation

Two independent defences failed in sequence:

1. **Coder prevention (upstream):** Rule 10 exists but omits the two-step requirement specific to agents — the `agent:` block entry alone is not enough when the dispatching orchestrator uses `"": "deny"`. A developer following the rule literally might add only the `agent:` block entry and not realise the allow-list is also required.

2. **Reviewer detection (downstream):** Neither Claude nor GPT read `opencode.json` when reviewing a PR that introduced a new `.opencode/agents/*.md` file. There is no explicit checklist item in Phase 1 of `code-review-process.md` requiring `opencode.json` inspection for new-agent PRs. The omission is structural — the config file is not in the diff, so it will not be read unless the reviewer is specifically prompted to look.

This pattern is a recurrence of issue #23 (compaction plugin not registered in `opencode.json`), which led to Coder Rule 10. The recurrence on a different artifact type (agent vs plugin) confirms the rule needs explicit per-artifact-type sub-bullets to close the remaining gaps.

A secondary event in this PR: the Coder timed out before making a git commit — all four files were written to disk but the commit did not happen. The Orchestrator detected the side effects and committed manually. This is a recurrence of the timeout-with-side-effects pattern already captured in issue #117 (`.github/notes/reflections/archive/issue-117-coder-timeout-side-effects-2026-04-21.md`). The existing `dispatch-retry.md` protocol covers this case; no new action needed.

A third event: the sub-phase label ordering conflict (7h before 7g) was caught by Claude and Gemini but missed by GPT. This is a known reviewer-divergence risk with no systemic fix beyond the current multi-model approach. The PR was fixed correctly before merge.

### Suggested Improvements

**Improvement A — `code-review-process.md`, Phase 1 (minor):**

Add a checklist item requiring direct inspection of `opencode.json` when a new agent file is introduced:

> - [ ] **`opencode.json` registration for new agents** — when any `.opencode/agents/*.md` file is **added**, always read `opencode.json` directly and verify: (1) the new agent is present in the `agent:` block; (2) any orchestrator with `"": "deny"` in `permission.task` has the new agent in its allow-list. Missing registration is not visible in the diff — it is a gap in files the diff does not touch. Do not infer registration from context; always read the file.

**Improvement B — `coder.agent.md`, Rule 10 (minor):**

Add a specific agent sub-bullet under the "Registration/discovery" bullet:

> - **New `.opencode/agents/*.md` files specifically:** Immediately after writing the agent file, update `opencode.json` with: (a) an entry in the `agent:` block defining the new agent; (b) the agent name in the `permission.task` allow-list of every orchestrator that uses `"": "deny"` as its default policy and will dispatch the new agent. Both entries are required — the `agent:` block defines the agent; the allow-list grants dispatch permission. An agent absent from the allow-list is silently denied at runtime with no indication from the agent file itself.

### Action Taken

Applied: Improvement A added to `code-review-process.md` Phase 1 structural review checklist, immediately before the `Shell snippet safety` item.
Applied: Improvement B added to `coder.agent.md` Rule 10, immediately before the existing tool-contract sub-bullet.
