---
date: "2026-04-14"
issue: 16
pr: 52
category: instruction
targets:
  - ".github/notes/gotchas.md"
severity: minor
status: active
---

## ChromaDB L2 distance-to-similarity: 1-d is wrong, use 1/(1+d)

### Finding

During issue #16 (PR #52), the wiki-search tool's initial implementation converted ChromaDB L2 distances to similarity scores using `1.0 - distance`. The Synthesized Review flagged this (★★☆, majority): L2 distances are unbounded (can exceed 1.0), making `1.0 - distance` produce negative scores.

The fix applied `1.0 / (1.0 + distance)`, which correctly maps `[0, ∞)` to `(0, 1]` — zero distance gives 1.0 (perfect match), large distances approach 0.0.

### Observation

This is a common mistake when working with ChromaDB's default L2 distance metric. Cosine similarity naturally maps to `[0, 2]` (often `1 - cosine_distance`), which is what developers expect. But ChromaDB's default is L2 (Euclidean), where the same formula breaks. This gotcha will recur in any future tool that queries ChromaDB and displays similarity scores.

The conventions collection (proposed in issue #7 reflection) would be the ideal place for this pattern. Since that collection doesn't exist yet, this reflection serves as the record.

### Suggested Improvement

When the conventions collection and `gotchas.md` are created (per issue #7 reflection), add this entry:

```markdown
### ChromaDB L2 Distance to Similarity

**Wrong:** `score = 1.0 - distance` — L2 distances are unbounded, produces negative scores.
**Right:** `score = 1.0 / (1.0 + distance)` — maps [0, ∞) → (0, 1].

ChromaDB default metric is L2 (Euclidean), not cosine. The `1 - d` formula only works for cosine distance which is bounded [0, 2].
```

### Action Taken

No action taken — target file (`gotchas.md`) does not exist yet. Recorded as a reflection for inclusion when the conventions collection is created (issue #7 dependency). Embedded into `reflections` ChromaDB collection for semantic recall.
