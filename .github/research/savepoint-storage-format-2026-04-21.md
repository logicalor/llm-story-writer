# Synthesized Research Report: Savepoint Storage Format

**Date:** 2026-04-21  
**Research question:** What is the most reliable and LLM-readable storage format to replace the current mixed markdown/JSON savepoint system in `llm-story-writer`?  
**Scope:** The `stories/<name>/savepoints/` directory and `src/infrastructure/storage/savepoint_repository.py`.

---

## Synthesis Overview

Three independent models researched five candidate formats (pure JSON, split-by-type, markdown with JSON code fences, YAML for everything, and a JSON envelope). All three models converged on the same diagnosis: the current system is broken because it embeds full markdown documents as escaped JSON string values inside `.md` files, a pattern that confuses both LLMs reading files directly and Python code loading them. Two of three models (Claude, GPT) recommend **Option B — split by extension** (`.md` for prose, `.json` for structured data) as the optimal replacement. The third model (Gemini) recommends YAML for everything (Option D), primarily to avoid having two code paths. The 2-vs-1 consensus and the specific nature of Gemini's objections (addressed below) favour Option B.

**Model Agreement Score: 7/10** — Strong agreement on problem diagnosis and on rejecting the worst options (pure JSON, JSON envelope); meaningful divergence only on the primary recommendation (B vs D).

---

## Individual Report Summaries

| Model  | Focus Areas | Unique Finds | Sources Cited |
| ------ | ----------- | ------------ | ------------- |
| Claude | LLM readability empirics, framework patterns, YAML edge cases, migration path | arXiv 2602.05447 (9,649-experiment multi-model study); agent file convention survey | 14 |
| GPT    | Framework-first analysis, AutoGen/LangGraph state-as-dict pattern, typed API recommendation | Explicit "do not self-detect format from file content" warning; paired `.json`+`.md` split for mixed-type savepoints | 8 |
| Gemini | YAML token efficiency advantage, PyYAML literal block scalar implementation | 30–56% token reduction with YAML vs JSON (tashif.codes study); ready-to-run custom representer code | 4 |

---

## Consensus Findings

### ★★★ Unanimous Findings (All Three Models Agree)

```
[U-01] Current system is a confirmed anti-pattern
Confidence: ★★★ Unanimous
Category: Architecture
Detail: All three models independently identified the same root failure: the system stores
full markdown documents as escaped JSON string values inside `.md` files. This produces
files that are unreadable to humans (escaped unicode, single-line blobs), confusing to
LLMs (they see JSON where every meaningful value is an escaped secondary document), and
fragile in Python (three loading code paths to handle legacy variants). No major AI agent
framework uses anything remotely similar; all frameworks separate structured state from
free-text artifacts.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: arXiv:2602.05447; docs.crewai.com; microsoft.github.io/autogen;
         reference.langchain.com
```

```
[U-02] `ensure_ascii=False` is required for any JSON output
Confidence: ★★★ Unanimous
Category: Correctness
Detail: The current `outline_consolidated.md` contains `\u2019` instead of `'` (and
similarly escaped smart quotes/dashes throughout). This is caused by Python's `json.dumps`
default of `ensure_ascii=True`. Every model noted this explicitly. Setting
`ensure_ascii=False` in all `json.dumps` and `json.dump` calls eliminates all unicode
escape sequences from stored files.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: docs.python.org/3/library/json.html
```

```
[U-03] Remove all three-way loading logic; no legacy branch needed
Confidence: ★★★ Unanimous
Category: Architecture
Detail: The current `load_savepoint()` has three dispatch paths: (1) YAML frontmatter with
`format: json` → parse body as JSON, (2) no frontmatter → parse with `**Value:**`/`**Type:**`
scalar markers, (3) other frontmatter → legacy YAML-as-data. All three models concluded this
complexity should be excised entirely. The replacement format should require a single,
deterministic loading call with no content sniffing.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: Project codebase analysis; framework documentation
```

```
[U-04] No YAML frontmatter in savepoint files
Confidence: ★★★ Unanimous
Category: Architecture
Detail: YAML frontmatter (`---`/`---` delimiters) in savepoints adds parsing overhead with
no benefit. The format hint it carries (`format: json`) is the symptom of the real problem
(wrong file format). All three models recommended eliminating frontmatter from savepoints
entirely. The wiki system correctly uses frontmatter in wiki pages (which are permanent
knowledge documents), but savepoints are transient pipeline artefacts and do not benefit
from it.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: Project codebase analysis
```

```
[U-05] Major AI agent frameworks use JSON or database backends for structured checkpoints
Confidence: ★★★ Unanimous
Category: Best Practice
Detail: LangGraph uses SQLite/Postgres with a JsonPlusSerializer. CrewAI defaults to one
`.json` file per checkpoint via JsonProvider (documented as "simple, human-readable, easy
to inspect") with SQLite as the high-frequency alternative. AutoGen persists state as
dictionary → `json.dump` to a `.json` file. No mainstream framework stores structured
state inside markdown or mixes the two formats in one file.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: docs.crewai.com/en/concepts/checkpointing; reference.langchain.com/python/langgraph;
         microsoft.github.io/autogen
```

```
[U-06] Prose savepoints (plain markdown, no JSON) work correctly today and should not change
Confidence: ★★★ Unanimous
Category: Architecture
Detail: Files like `base_context.md`, `outline_chunk_1_10.md`, `continuity_1_10.md`, and
`understand_prompt.md` are already clean, readable, and well-suited to their purpose. All
three models confirmed these should not be changed — the problem is exclusively in the
structured-data savepoints that were forced into `.md` wrappers.
Models: Claude ✓ GPT ✓ Gemini ✓
Sources: Direct examination of story savepoint files
```

---

### ★★☆ Majority Findings (Two of Three Models Agree)

```
[M-01] Option B (split by extension) is the best overall replacement
Confidence: ★★☆ Majority
Category: Architecture
Detail: Claude and GPT both recommended Option B: use `.md` extension for prose savepoints
(no change to existing clean files) and `.json` extension for structured data savepoints
(pure JSON, no markdown wrapper, no frontmatter). Extension alone determines the loader —
one branch per suffix, each a single stdlib call:

  if path.suffix == ".json":
      return json.loads(path.read_text(encoding="utf-8"))
  return path.read_text(encoding="utf-8")

Claude's overall rating: 6/7 requirements ✅.
GPT noted only req 4 as ⚠️ (two paths, not one), and assessed this as trivially acceptable.
Models: Claude ✓ GPT ✓ Gemini ✗
Dissenting view (Gemini): Rated Option B ❌ for requirements 1, 4, and 7. Gemini's argument
was that "a structured list of chapters where each chapter contains a prose outline cannot
be cleanly split without extreme fragmentation." This objection assumes the `outline_consolidated`
pattern (markdown documents embedded as JSON values) is a feature to be preserved. Both Claude
and GPT correctly identified it as the defect to be eliminated, not accommodated. The response
to Gemini's concern is covered in [M-02] and [U-01].
Sources: arXiv:2602.05447; docs.crewai.com; docs.python.org
```

```
[M-02] When a structured savepoint needs prose content, use separate companion files
Confidence: ★★☆ Majority
Category: Architecture
Detail: Claude and GPT both converged on the same design principle: a `.json` savepoint
should store metadata (chapter number, title, who, what) with short prose summaries only.
Long prose belonging to a chapter (full outline text, character description, etc.) belongs
in a companion `.md` savepoint, referenced by name if needed. This directly resolves the
`outline_consolidated` problem: instead of one file with embedded markdown-as-JSON-string,
there are two files — `outline_consolidated.json` with chapter metadata and
`outline_chunk_1_10.md` with prose outlines. Both files already exist in the codebase;
they just need the consolidated file to stop re-embedding the prose.
Models: Claude ✓ GPT ✓ Gemini ✗
Dissenting view (Gemini): Gemini preferred a single YAML file that handles both, using
block scalars for the prose fields. This is technically valid but adds YAML 1.1 edge cases
and a non-stdlib dependency.
Sources: Project codebase analysis; researcher recommendations
```

---

### ★☆☆ Singular Findings (Only One Model Reported)

```
[S-01] Empirical LLM readability: YAML outperforms JSON by 2-12% across most frontier models
Confidence: ★☆☆ Singular
Category: Performance
Detail: Claude cited arXiv:2602.05447 (McMillan, Feb 2026): 9,649 experiments across
11 models found YAML achieved 75.4% accuracy vs JSON's 72.3%. The advantage is 4–12%
for Claude-family models specifically. ImprovingAgents.com study corroborated: YAML best for
GPT-5 Nano and Gemini 2.5 Flash Lite; JSON best for Llama 3.2 3B. Critically, these studies
tested structured schema files, not prose — so the advantage is specifically for the
structured-data savepoints, not the prose ones.
Model: Claude
Assessment: Plausible and consistent with known YAML readability advantages. Does not
change the Option B recommendation (which uses .json for structured data) unless the
project's LLM is exclusively Claude-family, in which case YAML may produce marginally
better agent comprehension of structured savepoints. The 2–3% difference is unlikely to
be decision-determinative given the other YAML complexity costs.
Sources: arxiv.org/abs/2602.05447; improvingagents.com
```

```
[S-02] Use explicit typed API at the repository boundary, not implicit extension detection
Confidence: ★☆☆ Singular
Category: Architecture
Detail: GPT recommended making the type contract explicit in the Python API:

    save_text_savepoint(name: str, content: str) -> None
    save_json_savepoint(name: str, content: dict | list) -> None
    load_text_savepoint(name: str) -> str
    load_json_savepoint(name: str) -> dict | list

This prevents a caller from accidentally calling `load_savepoint("outline_consolidated")`
and receiving a string instead of a dict. GPT also warned against detecting format from
file contents (the current `format: json` frontmatter pattern) — use the extension or a
caller-explicit API instead.
Model: GPT
Assessment: Good engineering principle. Option B already solves the detection problem via
extension. The explicit typed API is a refinement that improves call-site clarity
and eliminates runtime type-surprise bugs. Worth considering during reimplementation.
Sources: Researcher recommendation
```

```
[S-03] YAML token efficiency advantage is 30-56% vs minified JSON
Confidence: ★☆☆ Singular
Category: Performance
Detail: Gemini cited tashif.codes study: YAML indentation-based structure uses fewer tokens
than JSON (no braces, no quotes on keys). The advantage is highest vs minified JSON and
smallest vs pretty-printed JSON. Project uses `indent=2` which closes the gap.
Model: Gemini
Assessment: Likely accurate for structured data. Less relevant for prose (both .md and
YAML literal block scalars are similar in token cost). The advantage would only be
meaningful if the project switches to YAML for everything rather than Option B.
Sources: tashif.codes/blog/JSON-YAML-LLM
```

```
[S-04] PyYAML YAML 1.1 gotchas are a genuine risk for story content
Confidence: ★☆☆ Singular
Category: Correctness
Detail: Claude noted that PyYAML (the stdlib-adjacent choice) uses YAML 1.1, which
interprets bare words `yes`, `no`, `on`, `off`, `true`, `false` as booleans. Story content
can contain these words naturally. A character named "No" or a plot point involving "off"
could be silently coerced. Using `ruamel.yaml` (YAML 1.2) avoids this but adds a second
non-stdlib dependency. Claude's custom representer code (from Gemini) does not fix this
issue since it only controls output format, not input parsing.
Model: Claude
Assessment: Real concern specific to narrative text. This is the strongest technical
argument against Option D (YAML for everything) in a story generation context. Story
prose contains many English words that YAML 1.1 treats as special. Not an issue for
Option B, which stores prose as raw `.md` text.
Sources: pyyaml.org/wiki/PyYAMLDocumentation; researcher analysis
```

---

## Divergence Analysis

```
[D-01] Topic: Option B (split .md/.json) vs Option D (YAML for everything)
Claude says: Option B is best. Matches industry convention. Stdlib only. Best format for
prose (.md) and best deterministic format for structured data (.json). YAML has dependency
and YAML 1.1 gotcha risks.
GPT says: Option B is best. The only approach that separates representation from structure
at the file level. Slightly weakens req 4 (two paths) but this is trivially acceptable.
Option D with PyYAML loses round-trip reliability for story prose containing YAML special words.
Gemini says: Option D (YAML) is best. YAML handles both categories in one format, one parser,
one code path. Block scalar (`|`) eliminates the need to split prose/structured data into
separate files. Token efficiency advantage for LLM context.

Assessment: Claude and GPT are most likely correct. Gemini's reasoning conflates two
separate problems: (1) how to store a mixed structured+prose savepoint in one file, and
(2) whether we should have mixed structured+prose savepoints at all. The actual design
lesson from the current mess is that mixed-type savepoints are the root cause of the
problem. Compelling the system to use a format that "handles both" in one file makes it
easier to reintroduce the same anti-pattern. Option B, by creating two separate file types,
makes it structurally harder: prose savepoints have no syntax for structured lists; JSON
savepoints have no convenient syntax for multi-paragraph prose — so developers are nudged
toward the correct separation.

The YAML 1.1 boolean coercion issue (S-04) also makes YAML measurably worse for story
text than either JSON or Markdown. Story prose regularly contains "yes", "no", "off", "on"
as natural English words. A prose block that accidentally triggers YAML coercion is a
debugging nightmare.

Resolution: Adopt Option B. For the rare case where a structured savepoint needs a prose
description in one field (e.g., a chapter's one-sentence summary), JSON can store it
cleanly as a short UTF-8 string with ensure_ascii=False. Full long-form prose belongs
in a companion .md savepoint.
```

---

## Recommendations

1. **[U-01][U-03] ★★★ Replace the three-way loading logic with extension-based dispatch.** The `load_savepoint` method becomes:
   ```python
   if path.suffix == ".json":
       return json.loads(path.read_text(encoding="utf-8"))
   return path.read_text(encoding="utf-8")
   ```
   Delete all frontmatter parsing, `**Value:**`/`**Type:**` pattern matching, and legacy YAML-as-data branches.

2. **[M-01][U-04] ★★☆ Switch structured savepoints from `.md` to `.json`.** Any savepoint that stores a Python dict or list should be saved as a pure `.json` file (no frontmatter, no markdown heading wrapper). The handful of affected savepoints: `outline_consolidated`, items under `story_analysis/`, `story_start_date` (scalar, becomes tiny JSON string).

3. **[U-02] ★★★ Set `ensure_ascii=False` on all `json.dumps` / `json.dump` calls.** This eliminates the current `\u2019` escaping throughout stored files.

4. **[M-02] ★★☆ Design rule: structured savepoints must not embed prose as JSON string values.** The `outline_consolidated` anti-pattern — storing entire markdown chapter outlines as escaped JSON string values — must not be reproduced. If a structured savepoint needs to reference prose (e.g., chapter content), it stores a short summary or references the prose savepoint by name.

5. **[U-06] ★★★ Leave existing prose savepoints unchanged.** `base_context.md`, `outline_chunk_1_10.md`, `continuity_1_10.md`, and all similar prose files are already correct. Change nothing about their format.

6. **[S-02] ★☆☆ Consider a typed repository API** (`save_text_savepoint`/`save_json_savepoint`) to make the type contract explicit at call sites and prevent accidental type confusion. If the single-method API is preferred, extension-based dispatch in `_get_savepoint_path` is sufficient.

---

## Gaps / Uncertainties

1. **`outline_consolidated.json` schema after migration.** The current `outline_consolidated.md` embeds full chapter outline markdown documents as JSON string values. After migration, those strings should be short summaries, not full markdown. But the exact new schema for the consolidated outline (what fields, how chapters reference prose) needs to be designed as part of implementation.

2. **Scalar savepoints** (`story_start_date.md` storing `2024-10-14`). These become one-element JSON files (`"2024-10-14"`) or remain as `.md` files (just raw text). The current `**Value:**`/`**Type:**` encoding for int/float/bool scalars should be evaluated — most likely they become `.json` files with the scalar value (`true`, `42`, `3.14`), which is valid JSON.

3. **`story_elements.md` with `=== Section ===` markers.** This file is a concatenation of sections separated by non-standard delimiters. It is unclear whether this is a single savepoint (should be one prose `.md`) or multiple savepoints accidentally merged. Investigation needed before migration.

4. **Test coverage for the new format.** The existing 57 passing tests cover the current three-way loading logic. After migration, tests will need to be updated to verify the new two-path extension-based loader and reject the old patterns.

---

## Combined Source List

- [arxiv.org/abs/2602.05447](https://arxiv.org/abs/2602.05447) — McMillan (Feb 2026): 9,649 experiments across 11 models, 4 file formats — cited by Claude
- [improvingagents.com/blog/best-nested-data-format](https://www.improvingagents.com/blog/best-nested-data-format/) — YAML vs JSON vs XML vs Markdown LLM accuracy benchmark — cited by Claude
- [docs.crewai.com/en/concepts/checkpointing](https://docs.crewai.com/en/concepts/checkpointing) — JsonProvider and SqliteProvider checkpoint patterns — cited by all three
- [reference.langchain.com/python/langgraph](https://reference.langchain.com/python/langgraph/checkpoints) — LangGraph `JsonPlusSerializer`, `SqliteSaver` — cited by Claude and GPT
- [microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/state.html](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/state.html) — AutoGen state save/load pattern — cited by GPT and Gemini
- [docs.python.org/3/library/json.html](https://docs.python.org/3/library/json.html) — `ensure_ascii` parameter documentation — cited by GPT and Gemini
- [pyyaml.org/wiki/PyYAMLDocumentation](https://pyyaml.org/wiki/PyYAMLDocumentation) — YAML 1.1 boolean coercion, custom representers — cited by Claude and Gemini
- [tashif.codes/blog/JSON-YAML-LLM](https://tashif.codes/blog/JSON-YAML-LLM) — YAML 30–56% token efficiency advantage — cited by Gemini
- [blogs.oracle.com/developers](https://blogs.oracle.com/developers/comparing-file-systems-and-databases-for-effective-ai-agent-memory-management) — File system vs database comparison for AI agent memory — cited by Claude
- [gist.github.com/0xdevalias/f40bc5a6f84c4c5ad862e314894b2fa6](https://gist.github.com/0xdevalias/f40bc5a6f84c4c5ad862e314894b2fa6) — Survey of AI agent rule/instruction/context file conventions — cited by Claude
