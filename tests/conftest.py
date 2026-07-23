"""Pytest configuration for bridge tests.

Sets up paths to allow imports from both the main repo and the worktree.
"""

import sys
import os

# Add main repo src to path
main_repo_src = os.path.join(os.path.dirname(__file__), "..", "..", "..", "src")
if main_repo_src not in sys.path:
    sys.path.insert(0, main_repo_src)

# Add worktree src to path
worktree_src = os.path.join(os.path.dirname(__file__), "..", "src")
if worktree_src not in sys.path:
    sys.path.insert(0, worktree_src)
