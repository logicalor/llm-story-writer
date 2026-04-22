---
date: "2026-04-22"
issue: 125
pr: 131
category: instruction
targets:
  - ".github/notes/gotchas.md"
severity: minor
status: archived
---

<!-- Archived. Full note in archive/issue-125-wiki-search-tool-contract-2026-04-22.md -->

## `wiki-search` operation name and parameter name gotcha

### Finding

During PR #131 (feat/issue-125-analytical-review-family), the `consistency-checker` agent
Step 2 called `wiki-search` with `operation: "search"` and `limit: 3`. Both values are wrong:

- `wiki-search.ts` defines `operation` as `z.enum(["semantic", "metadata"])` — `"search"` is
  not a valid enum value and is rejected by Zod at runtime.
- The count parameter key is `nResults` (line 22 of `wiki-search.ts`), not `limit`.

The error is an isolated authoring mistake: Step 3 of the same file correctly uses `nResults`
for the `rag-query` call, confirming the author understood the pattern for one tool but
misremembered the operation enum and parameter name for `wiki-search`.

**Identified by:** GPT and Gemini independently (majority Critical, M-C-01). Claude missed it
and assessed tool call contracts as "verified correct." Direct TS source inspection confirms
the two GPT/Gemini findings. Operating value `"semantic"` is the correct default for
free-text wiki queries; `"metadata"` is for structured field matching.

### Observation

The Coder rule for schema conformance (Rule 10, "When writing or editing any agent or skill
content…") requires verifying parameter names against the Zod field names in the TS wrapper —
but it is a general instruction. A specific gotcha entry for `wiki-search` makes the correct
values immediately discoverable when the rule fires, without requiring the Coder or reviewer
to open the TS source.

The distinction between `operation: "semantic"` (natural language querying) and
`operation: "metadata"` (structured field matching) is also worth documenting as a usage note.

### Suggested Improvement

Add a gotcha entry to `.github/notes/gotchas.md` under the **Tool CLI Interface** section:

```markdown
### 010 — `wiki-search`: valid operation values are `"semantic"` and `"metadata"` — not `"search"`

**Source:** issue #125, PR #131
**Severity:** warning

`wiki-search` defines its `operation` parameter as `z.enum(["semantic", "metadata"])` in
the TypeScript wrapper. The value `"search"` is not in the enum and is rejected by Zod
at runtime.

| Value | Use |
|-------|-----|
| `"semantic"` | Natural-language free-text query (default for most wiki lookups) |
| `"metadata"` | Structured field matching (filter by page type, tags, etc.) |

The count parameter is `nResults`, not `limit`.

# Wrong:
wiki-search --operation search --limit 3 …
# Right:
wiki-search --operation semantic --nResults 3 …
```

### Action Taken

Applied: Added gotcha entry 010 to `.github/notes/gotchas.md` under the Tool CLI Interface
section, after entry 005.
