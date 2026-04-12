# Legacy Codebase Archive

This directory contains a frozen copy of the original `src/` directory, taken before the OpenCode Agentic Architecture Migration began.

## Purpose

- **Reference during migration** — developers can consult this archive to verify that migrated tool behaviour matches the original pipeline
- **Frozen snapshot** — this code should NOT be modified; it exists purely as a historical reference

## Contents

- `src/` — complete copy of the original source tree (Python domain logic, infrastructure, application services, CLI)

## Relationship to Active Codebase

The active `src/` directory at the repository root continues to be restructured incrementally during migration. This archive preserves the pre-migration state for comparison.

## When to Remove

This archive can be removed once the migration is complete and all tool behaviours have been verified against the original implementation.
