#!/usr/bin/env bash
set -euo pipefail

# Run the node's test suite; exit 0 on success, non-zero on failure
# -----------------------------------------------------------------

cd /Users/nealpatel/Code/l-system/.worktrees/main.bridge.translate

# Set PYTHONPATH to include src and parent directories
export PYTHONPATH="/Users/nealpatel/Code/l-system/src:/Users/nealpatel/Code/l-system/.worktrees/main.bridge.translate/src:${PYTHONPATH:-}"

# Run pytest on bridge translate tests
python -m pytest tests/test_bridge_translate.py tests/test_bridge_identity.py -v
