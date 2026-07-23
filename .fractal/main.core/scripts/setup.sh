#!/usr/bin/env bash
set -euo pipefail

# Environment setup -- runs at the start of every iteration
# ---------------------------------------------------------
#
# Must be idempotent. Update this script instead of installing
# packages inline, so the environment stays reproducible across
# iterations. The loop activates the repo venv automatically.

# core node: sync the project venv into the worktree-local .venv.
# Pinned to Python 3.13 — coincurve ships no cp314 wheels yet, and the
# shared repo .venv (3.14) must stay untouched for sibling nodes.
if command -v uv &>/dev/null; then
    UV_PYTHON=3.13 uv sync --inexact --quiet
fi
