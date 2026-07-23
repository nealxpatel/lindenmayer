"""Pytest configuration for Lindenmayer kinds tests."""

import sys
from pathlib import Path

# Add tests directory to path so relay_mock can be imported
tests_dir = Path(__file__).parent / "tests"
if str(tests_dir) not in sys.path:
    sys.path.insert(0, str(tests_dir))
