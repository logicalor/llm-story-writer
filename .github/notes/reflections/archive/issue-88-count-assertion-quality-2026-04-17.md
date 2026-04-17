---
date: "2026-04-17"
issue: 88
pr: 91
category: agent
targets:
  - ".github/agents/test-writer.agent.md"
severity: minor
status: archived
---

## Count-only assertions on collection results are insufficient — content must be verified

### Finding

During issue #88 (Integration test: wiki-read path has no coverage), the Test Writer wrote a `test_wiki_read_match_entities` method containing only a count assertion:

```python
assert len(data["matches"]) >= 1
```

This was flagged as S-01 (weak assertion) during code review and immediately fixed by the Orchestrator to verify specific entity names:

```python
matched_names = {m["name"] for m in data["matches"]}
assert matched_names & {"Alex", "ARIA", "Neo-Tokyo"}
```

### Observation

Count-only assertions confirm that *something* was returned, but not that the returned data is correct. For operations like entity matching, the intent is to retrieve specific known entities — confirming count does not verify that the right entities were matched.

This is the third instance of this pattern appearing in review findings:
- **Issue #8** — `test_write_missing_value` had no assert at all
- **Issue #15** — bare `except: pass` obscured assertion reachability
- **Issue #88** — count-only assertion on match results

The Test Writer's guidance covers priority order (validation → happy path → error → integration) and running tests incrementally, but does not address assertion *quality* — specifically that collection results must verify specific expected values, not just existence or count.

### Suggested Improvement

Add a **Collection Assertions** note to the Test Writer's "Write Tests" section, immediately after the priority order list:

```markdown
**Collection assertions:** When asserting on lists, sets, or decoded JSON arrays returned by a tool or API, verify specific expected values — not just count or existence. `len(results) >= 1` only confirms something was returned; it does not confirm correctness. Use subset membership (`assert expected_set <= actual_set`), intersection (`assert expected_set & actual_set`), or item-level checks (`assert any(item["name"] == "expected" for item in results)`) to confirm the returned data is meaningful and correct.
```

### Action Taken

Applied: added collection assertion guidance to `.github/agents/test-writer.agent.md` in the "Write Tests" section, after the priority order list.
