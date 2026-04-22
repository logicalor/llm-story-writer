---
date: "2026-04-22"
issue: 121
pr: 128
category: agent
targets:
  - ".github/agents/coder.agent.md"
  - ".github/agents/_shared/review-checklist.md"
severity: minor
status: archived
---

## TS `.optional()` does not reflect Python backend conditional requirements — `sceneNum` omitted caused hard fail

### Finding

During PR #128 (feat: final-editor and prose-scrubber subagents), both the `final-editor` and `prose-scrubber` agents called `scene-writer` with `operation: "revise"` but omitted `sceneNum`. The TypeScript wrapper marks `sceneNum` as `.optional()` in the Zod schema. However, `src/tools/scene_writer.py:376` performs a manual conditional check: when `operation == "revise"`, the absence of `--scene-num` triggers a hard exit. The defect was only caught in review; neither agent had been executed at the time.

Defect code: **[M-C-01]** — classified Critical by all three reviewer models.

This is the fifth consecutive occurrence of the tool-contract verification defect class (issues #19, #22, #113, #115, #120). All previous occurrences involved wrong values, wrong key names, or wrong operation names. This occurrence introduces a new sub-class: **operation-conditional required parameters** — a parameter that is unconditionally `.optional()` in the TS Zod schema but conditionally `required` in the Python backend depending on the active `operation` value.

### Observation

The existing Rule 10 verification checklist (items a–d) addresses: operation name correctness, Zod type correctness, return value shape, and parameter key names. None of these items explicitly direct the Coder to check whether a conditionally required Python parameter is being passed for the relevant operation. A Coder reading the TS wrapper will see `.optional()` and reasonably conclude the parameter is safe to omit — without checking the Python source for conditional logic.

The Zod schema accurately describes the TS contract (the JSON payload is valid with or without `sceneNum`). But validity at the TS layer does not guarantee validity at the Python layer. Python tools frequently use `if args.operation == X and not args.param: sys.exit(2)` patterns that are invisible to the TS wrapper.

This gap creates a systematic blind spot: any parameter that is TS-`.optional()` but Python-conditionally-required will be missed by checks (a)–(d) as currently written.

### Suggested Improvement

**Change 1 — coder.agent.md Rule 10 extension (item e):**

Extend the existing Rule 10 verification list from four items to five:

> (e) when a parameter is marked `.optional()` in the Zod schema, verify in the Python source whether it is unconditionally optional or conditionally required based on the active operation — Python tools frequently use conditional argparse validation (`if args.operation == "X" and not args.param: sys.exit(2)`) that is not reflected in the TS `.optional()` declaration; omitting a conditionally required parameter produces a hard exit at runtime with no indication from the Zod schema.

**Change 2 — review-checklist.md Phase 2 Agent Instructions item (d):**

Extend the `Tool call contracts` item with a fourth verification point:

> (d) any TS parameter marked `.optional()` that is omitted for a specific operation — verify in the Python source that the field is genuinely optional for the active `operation`; Python tools use conditional validation (`if args.operation == "revise" and not args.scene_num: sys.exit(2)`) that the Zod schema cannot represent; `.optional()` reflects TS schema permissiveness only.

### Action Taken

Applied: added item (e) to Rule 10 in `.github/agents/coder.agent.md` and added item (d) to the Tool call contracts checklist entry in `.github/agents/_shared/review-checklist.md`.
