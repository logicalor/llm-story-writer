# Multi-Model Synthesis — Shared Workflow

> Shared protocol for agents that coordinate multiple LLM models and synthesize their outputs into a consensus report. Include this file in any synthesizing agent.

---

## Why Three Models?

Different LLMs have different strengths, blind spots, and reasoning biases. By running the same process across three independent models and synthesizing the results, this agent:

- **Increases confidence**: findings reported by all three models are very likely genuine
- **Reduces false positives**: a finding from only one model may be a hallucination or misinterpretation
- **Surfaces broader coverage**: each model may notice things the others miss
- **Provides perspective diversity**: different reasoning approaches catch different categories of issues

---

## Models

| Role suffix | Model | Provider |
| ----------- | ----- | -------- |
| (Claude)    | Claude Opus 4.6 | Copilot |
| (GPT)       | GPT 5.4 | Copilot |
| (Gemini)    | Gemini 3.1 Pro (Preview) | Copilot |

---

## Dispatch

Dispatch all three sub-agents **sequentially** — invoke each `runSubagent` call one at a time and wait for it to complete before starting the next. Each receives the **same prompt**. Complete all three before proceeding.

> **Do NOT dispatch sub-agents in parallel.** Parallel execution causes stability issues and is forbidden. Always wait for each sub-agent to return before dispatching the next.

---

## Cross-Reference and Classify

For every finding across all three reports, determine its **consensus level**:

| Consensus | Definition | Confidence |
| --------- | ---------- | ---------- |
| **Unanimous** | All three models reported the same finding | ★★★ High |
| **Majority** | Two of three models reported a similar finding | ★★☆ Medium |
| **Singular** | Only one model reported this finding | ★☆☆ Low |

When classifying, match findings by **substance**, not exact wording. Two findings are "the same" if they identify the same issue in the same area, even if described differently or assigned different severity levels.

---

## Divergence Analysis

Identify areas where the models **disagreed**:

- **Severity disagreement**: Same finding, different severity
- **Contradictory findings**: One model says X is correct, another says X is wrong
- **Unique perspectives**: Findings only one model surfaced — assess whether genuine or likely false positive

With three models, a 2-vs-1 split is strong evidence against the outlier.

---

## Synthesize

Produce the final report (format defined in the calling agent) incorporating the best findings from all three models with appropriate confidence weighting.

---

## Consensus Finding Format

```
[U-C-01] Title
Severity: Critical | Warning | Suggestion
Category: Security | Correctness | Performance | Style | Testing | Documentation | Architecture
Detail: Synthesised description incorporating insights from all three models
Models: Claude ✓ GPT ✓ Gemini ✓
Suggestion: How to fix it
```

For non-unanimous findings, include `Dissenting view: What the minority models said`.

---

## Individual Report Summary Format

| Model | Overall Assessment | Unique Focus Areas | [Domain] Count |
| ----- | ------------------ | ------------------ | -------------- |
| Claude | ... | ... | N |
| GPT | ... | ... | N |
| Gemini | ... | ... | N |

---

## Divergence Format

```
[D-01] Topic: [area of disagreement]
Claude says: ...
GPT says: ...
Gemini says: ...
Assessment: Which view is most likely correct (with evidence)
```
