"""Pytest configuration for Lindenmayer bridge tests."""

import sys
from pathlib import Path

# Add src and tests directories to path so imports work correctly
# This allows tests to import from the worktree's src/ directory
base_dir = Path(__file__).parent
src_dir = base_dir / "src"
tests_dir = base_dir / "tests"

for d in [src_dir, tests_dir]:
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))
