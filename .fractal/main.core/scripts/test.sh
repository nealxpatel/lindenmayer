#!/usr/bin/env bash
set -euo pipefail

# Run the node's test suite; exit 0 on success, non-zero on failure
# -----------------------------------------------------------------

# No-op by default; extend per node with the project's test command.

# core node: run the library test suite from the worktree root.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
WORKTREE_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$WORKTREE_DIR"
UV_PYTHON=3.13 uv run --inexact pytest tests/ -q
