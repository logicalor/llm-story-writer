# AGENTS.md — llm-story-writer

## Project

**Name:** llm-story-writer
**Purpose:** AI-powered long-form story generation system

## Architecture

This project uses a **Python-native architecture**. Python scripts handle orchestration, tool execution, and domain logic. Prompt templates in `prompts/agents/` define agent behaviour.

### Clean Architecture Layers

```
src/domain/       → Entities, value objects (core business rules)
src/application/  → Strategies (use cases); services/ layer retired per ADR 008
src/infrastructure/ → Providers, storage (external adapters)
```

Each layer depends only on inner layers: infrastructure → application → domain. Domain has no external dependencies.

### Tools

Tools are **Python scripts** in `src/tools/` that implement deterministic domain logic (story state, wiki management, savepoints, generation). No TypeScript or subprocess wrappers exist.

### Agents

Story generation agent prompt files are defined in `prompts/agents/` and loaded via `src/infrastructure/prompts/agent_prompt_loader.py`. The primary agent is `story-orchestrator`, which coordinates the full generation pipeline. Subagents (`outline-planner`, `character-sheet-generator`, `chapter-writer`, `wiki-maintainer`, `quality-reviewer`) handle specialised creative tasks.

Migration work also uses Opencode agent files under `.opencode/agents/`. The migration inventory is now complete: 24 Markdown agent files covering `orchestrator-v3`, the specialist sub-agents, the reviewer family, the researcher family, the auditor family, and the standalone agents `pr-reviewer`, `planner`, `contemplator`, and `sprint-runner`. The researcher family and the auditor family (`auditor.md`, `auditor-kimi.md`, `auditor-qwen.md`, `auditor-glm.md`) depend on developer-local Tavily and Context7 MCP servers configured in `~/.config/opencode/opencode.json`; the checked-in `opencode.json` keeps only project-level runtime settings plus Chroma.

### Runtimes

Two agent runtimes are active during the migration transition period:

- **Opencode** (active development surface): agents in `.opencode/agents/` invoked via `opencode run @agent-name`. Uses OpenRouter-backed models (Kimi K2.6, Qwen3.6 Plus, GLM 5.1) via the project-level `opencode.json`.
- **GitHub Copilot** (preserved artefacts): agents in `.github/agents-copilot/` invoked via the `@agent-name` syntax in VS Code Chat. Uses native Copilot model selection.

**Dual-run policy:** Any change to an agent's behaviour must be applied to both runtimes during the transition. The canonical source will be designated in a future decision. See [Opencode Runtime Configuration](docs/features/opencode-runtime.md) for the full dual-run policy and the agent migration mapping table.

### Skills

Story generation skills are defined in `prompts/skills/`. The `story-pipeline` skill provides the pipeline reference (phases, quality gates, savepoints, config settings).

### Codex Workflow Skills

Codex-native development workflows live in `.agents/skills/`. These are the canonical workflow instructions for Codex sessions in this repository:

- `project-memory` — `.github/notes/` and ChromaDB recall protocol
- `github-workflow` — issue/branch/implementation/verification/PR lifecycle
- `reflection` — agent-system improvement notes, collation, and safe workflow instruction updates
- `planning-workflow` — PRDs, ADRs, task breakdowns, and implementation plans
- `code-review` — local and PR review process, including synthesis guidance
- `synthesized-audit` — repository healthchecks using persona-based consensus synthesis
- `test-verification` — test-writing and verification rules
- `documentation-maintenance` — docs, ADR, README, and companion-file updates
- `web-research` — current external research with Tavily, Context7, and primary sources

Older VS Code/GitHub Copilot agent definitions remain under `.github/agents-copilot/` for reference and Copilot use. Do not treat their `tools:` frontmatter or `github/...` tool names as directly callable by Codex; translate through the Codex workflow skills first.

### Storage

- Stories are stored in `stories/<name>/` directories with JSON state files
- Prompt templates are Markdown files in the top-level `prompts/` directory
- ChromaDB vector collections provide semantic search per story

### Model Configuration

Local LLM inference via any OpenAI-compatible endpoint — **LM Studio** (default: `http://127.0.0.1:1234/v1`), Ollama, or llama.cpp. Multiple model roles can be configured for different tasks (generation, analysis, embedding).

## Conventions

- **Python:** `snake_case` naming, `ruff` for linting/formatting, `pytest` for testing
- **Import order:** stdlib → third-party → local, alphabetised within groups
- **Testing:** `tests/unit/`, `tests/integration/`; name files `test_<module>.py`, methods `test_<behaviour>()`

## Commands

| Purpose        | Command                        |
| -------------- | ------------------------------ |
| Lint (fix)     | `ruff check --fix .`           |
| Format         | `ruff format .`                |
| Type check     | `mypy src/`                    |
| Full tests     | `pytest`                       |
| Single test    | `pytest tests/unit/test_<module>.py -v` |

## Important Rules

- Do not recreate deleted legacy archives or ad-hoc root utility scripts without a current design need.
- Never hardcode credentials or environment-specific values.
- Always validate at system boundaries.
- Run lint and type checks after every change.
