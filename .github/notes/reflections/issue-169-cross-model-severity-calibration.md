---
date: "2026-04-25"
issue: 169
pr: 178
category: instruction
targets:
  - ".github/agents/_shared/review-checklist.md"
severity: minor
status: active
---

## Claude systematic under-rating of serialization correctness bugs

### Finding

In PR #178, Claude classified the `to_string()` hardcoding bug (stored value would always be `"openai-compat"` regardless of provider) as S-02 **Suggestion** severity. GPT and Gemini both independently ranked it **Warning** and **Critical** respectively. The Synthesizing Reviewer correctly produced a ★★☆ majority finding at Warning level, but Claude's lower rating created a divergence that required explicit resolution.

A broken serialization round-trip is a silent state corruption defect: the provider key is stored in the wrong representation, and any future `from_string()` call on that stored value either fails or maps to the wrong provider. This is not a style preference — it is a correctness defect with guaranteed data loss in production.

### Observation

The review checklist has no guidance on severity anchoring for serialization defects. Without an explicit anchor, a reviewer may classify "to_string() returns wrong key for new provider" as a style/cleanup suggestion (no immediate test failure if the new key is not yet in active use) rather than a Warning correctness defect (broken invariant: the serialization contract guarantees round-trip fidelity).

This is the second recorded example of a serialization class of bug receiving under-weighted severity (cf. issue #159 `temperature=0` behavioral parity, also only one of three reviewers flagging it).

### Suggested Improvement

Incorporate a severity anchoring note into the new **Serialization round-trip completeness** checklist item (see `issue-169-serialization-roundtrip-completeness.md`): missing or incorrect entries in any of the three serialization surfaces are **Warning minimum** — they represent broken state-persistence contracts, not style choices.

This anchoring note also serves as a signal to the Synthesizing Reviewer: if Claude rates a serialization correctness finding below Warning while the majority rates it Warning/Critical, the synthesis should treat the lower rating as suspect and adopt the majority severity.

### Action Taken

Applied: severity anchoring note (`Warning minimum`) embedded within the new `Serialization round-trip completeness` checklist item in `.github/agents/_shared/review-checklist.md`.
