#!/usr/bin/env bash
#
# Pre-commit hook stub.
# Customize this script to run your project's linting, formatting,
# and test commands on staged files before each commit.
#
# To install: ./.github/scripts/install-hooks.sh
#

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

cecho() {
    printf '%b\n' "$*"
}

# Get list of staged files
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM)

if [ -z "$STAGED_FILES" ]; then
    cecho "${GREEN}✓ No staged files to check${NC}"
    exit 0
fi

# --- Add your project-specific checks below ---
# Examples:
#
# Lint:
#   npm run lint -- $STAGED_FILES
#   ruff check $STAGED_FILES
#   composer lint
#
# Type check:
#   npx tsc --noEmit
#   mypy .
#
# Tests:
#   pytest
#   npm test
#
# Uncomment and customize the checks your project needs.

cecho "${GREEN}✓ Pre-commit checks passed${NC}"
exit 0