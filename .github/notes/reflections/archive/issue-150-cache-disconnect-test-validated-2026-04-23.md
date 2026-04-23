---
date: "2026-04-23"
issue: 150
pr: 151
category: agent
targets:
  - ".github/agents/test-writer.agent.md"
severity: minor
status: archived
---

## Cache-disconnect pattern caught by semantic test — validated

### Finding

Issue #150 added a resumability cache to the `wiki-extract` tool. The Test Writer included `test_initial_populate_cache_hit_skips_llm`, which asserts that cached `detail_levels` appear in the actual `run_batch` payload delivered to the LLM layer — not merely that the LLM was not called. The Synthesized Review explicitly checked for the cache-disconnect pattern first observed in issue #15 and confirmed the test properly bridges cache state to consumer behaviour.

### Observation

This is the second validation event for the cache-disconnect rule (issue #15 addendum, also reinforced by issue #10 semantic-correctness guidance):

- Issue #15 (2026-04-14): cache populated but never read — disconnect invisible because tests only checked cache stats
- Issue #150 (2026-04-23): cache correctly wired; test asserts cached values reach the outgoing payload

The pattern is now reliably detected. The Test Writer's "Independent expected values" and "collection assertions" rules, plus the semantic-correctness rule from issue #10, together produce tests that verify integration, not just internal state. Reviewers now explicitly screen for this pattern, so the rule is effectively tripled-layered (writer → reviewer → synthesis).

### Suggested Improvement

None. The existing guidance is working as intended. This note records a second successful application to strengthen the evidence base for the rule.

### Action Taken

No code change. Recorded as positive validation of existing test-writer and reviewer guidance. Embedded to `reflections` collection for recurrence tracking.
