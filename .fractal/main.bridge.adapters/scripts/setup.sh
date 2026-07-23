#!/usr/bin/env bash
set -euo pipefail

# Environment setup -- runs at the start of every iteration
# ---------------------------------------------------------
#
# Must be idempotent. Update this script instead of installing
# packages inline, so the environment stays reproducible across
# iterations. The loop activates the repo venv automatically.

# Install the project in development mode
cd /Users/nealpatel/Code/l-system/.worktrees/main.bridge.adapters
pip install -e .
