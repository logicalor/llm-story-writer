#!/bin/sh
#
# Install git hooks from the repository into .git/hooks
# Run this after cloning the repository
#

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"

echo "Installing git hooks..."

# Install pre-commit hook (symlink so edits take effect immediately)
if [ -f "$SCRIPT_DIR/pre-commit-hook.sh" ]; then
    ln -sf "$SCRIPT_DIR/pre-commit-hook.sh" "$HOOKS_DIR/pre-commit"
    echo "✓ Installed pre-commit hook (symlink)"
else
    echo "✗ pre-commit-hook.sh not found"
    exit 1
fi

echo "Git hooks installed successfully!"
echo ""
echo "The pre-commit hook will automatically run linting and tests"
echo "on staged files before each commit."