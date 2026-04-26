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

### Skills

Story generation skills are defined in `prompts/skills/`. The `story-pipeline` skill provides the pipeline reference (phases, quality gates, savepoints, config settings).

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
