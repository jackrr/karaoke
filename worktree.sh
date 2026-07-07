#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <branch-name>"
  exit 1
fi

BRANCH="$1"

SRC_DIR="$(git rev-parse --show-toplevel)"

# Normalize branch name to directory name (e.g. jr/rule-iteration -> jr-rule-iteration)
DIR_NAME="${BRANCH//\//-}"
WORKTREE_DIR="$SRC_DIR/worktrees/$DIR_NAME"

if [ -d "$WORKTREE_DIR" ]; then
    echo "Error: $WORKTREE_DIR already exists. Remove it first or choose a different path."
    exit 1
fi

echo "Creating worktree at $WORKTREE_DIR on branch '$BRANCH'..."
if git -C "$SRC_DIR" show-ref --verify --quiet "refs/heads/$BRANCH"; then
    git -C "$SRC_DIR" worktree add "$WORKTREE_DIR" "$BRANCH"
else
    echo "Branch '$BRANCH' does not exist, creating it..."
    git -C "$SRC_DIR" worktree add -b "$BRANCH" "$WORKTREE_DIR"
fi

echo "Copying untracked files..."
untracked_files="$(git -C "$SRC_DIR" ls-files --others --exclude-standard)"
if [ -n "$untracked_files" ]; then
    while IFS= read -r file; do
        echo "  $file"
        dest="$WORKTREE_DIR/$file"
        mkdir -p "$(dirname "$dest")"
        cp "$SRC_DIR/$file" "$dest"
    done <<< "$untracked_files"
fi

cd "$WORKTREE_DIR"

echo "=== Working in $WORKTREE_DIR ==="

# Copy .pi* dirs from the repo root worktree into the new one
for src in "$SRC_DIR"/.pi*; do
  [[ -d "$src" ]] || continue
  base="$(basename "$src")"
  cp -a "$src" "$WORKTREE_DIR/$base"
done

pids=()
echo "Running uv sync in backend..."
(cd backend && uv sync) &
pids+=($!)

echo "Running bun install in frontend..."
(cd frontend && bun install) &
pids+=($!)
for pid in "${pids[@]}"; do wait "$pid"; done

echo "Done. Worktree is at: $WORKTREE_DIR"
