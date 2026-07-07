#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <branch-name> <initial-prompt>"
  exit 1
fi

BRANCH="$1"
PROMPT="$2"

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

# Create the branch (from main or master)
if git rev-parse --verify main &>/dev/null; then
  BASE="main"
elif git rev-parse --verify master &>/dev/null; then
  BASE="master"
else
  echo "No main or master branch found. Aborting."
  exit 1
fi

git checkout -b "$BRANCH" "$BASE"

# Create worktree in a sibling directory
WORKTREE_DIR="$REPO_DIR/worktrees/$BRANCH"
git worktree add "$WORKTREE_DIR" "$BRANCH"

cd "$WORKTREE_DIR"

echo "=== Working in $WORKTREE_DIR ==="

# Copy .pi* dirs from the repo root worktree into the new one
for src in "$REPO_DIR"/.pi*; do
  [[ -d "$src" ]] || continue
  base="$(basename "$src")"
  cp -a "$src" "$WORKTREE_DIR/$base"
done

# Install frontend deps
cd frontend
bun install
cd ..

# Install backend deps
cd backend
uv sync
cd ..

# Start pi with the initial prompt
# Using the first available method to invoke pi
exec pi -p "$PROMPT"
