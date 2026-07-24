#!/usr/bin/env bash
set -euo pipefail

# Environment setup -- runs at the start of every iteration
# ---------------------------------------------------------
#
# Must be idempotent. Update this script instead of installing
# packages inline, so the environment stays reproducible across
# iterations. The loop activates the repo venv automatically.

# The shared repo venv is Python 3.14, but coincurve (lindenmayer.core's
# secp256k1 dependency) ships no cp314 wheels and fails to build from
# source. Use a worktree-local 3.13 venv instead (wiki/node_operations.md).
# The loop runs this script from the worktree root, so relative paths
# (pyproject.toml, uv.lock) resolve correctly without a cd.
UV_PYTHON=3.13 uv sync --inexact
