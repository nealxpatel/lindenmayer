#!/usr/bin/env bash
set -euo pipefail

# Run the node's test suite; exit 0 on success, non-zero on failure
# -----------------------------------------------------------------

# Worktree-local 3.13 venv (see setup.sh) -- coincurve has no cp314 wheels.
UV_PYTHON=3.13 uv run --inexact pytest tests/ -q
