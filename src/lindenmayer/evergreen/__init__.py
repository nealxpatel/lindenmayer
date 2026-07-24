"""Evergreen: the human's read-only standing context surface over the signed log.

DESIGN.md §5.1: evergreen v1 is the read plane. It ships a typed query
library over the nine published event kinds (``query.py``), a generator for
the composite ``CONTEXT.md``-shaped standing surface (``surface.py``), and a
history query CLI (``cli.py``). No write path lives here.
"""

from __future__ import annotations
