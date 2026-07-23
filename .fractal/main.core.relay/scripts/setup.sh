#!/usr/bin/env bash
set -euo pipefail

# Environment setup -- runs at the start of every iteration
# ---------------------------------------------------------
#
# Must be idempotent. Update this script instead of installing
# packages inline, so the environment stays reproducible across
# iterations. The loop activates the repo venv automatically.

# Sync the project venv into the worktree-local .venv (Python 3.13 —
# coincurve ships no cp314 wheels; the shared repo .venv stays untouched).
if command -v uv &>/dev/null; then
    UV_PYTHON=3.13 uv sync --inexact --quiet
fi
