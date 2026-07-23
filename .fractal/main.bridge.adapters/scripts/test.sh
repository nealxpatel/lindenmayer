#!/usr/bin/env bash
set -euo pipefail

# Run the node's test suite; exit 0 on success, non-zero on failure
# -----------------------------------------------------------------

# Run adapter fixture tests
cd /Users/nealpatel/Code/l-system/.worktrees/main.bridge.adapters
python -m pytest tests/test_adapters.py -v
