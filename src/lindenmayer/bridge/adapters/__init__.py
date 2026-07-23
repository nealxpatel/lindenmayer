"""Adapters for reading Fractal's SQLite DB and session transcripts.

Provides read-only access to:
- per-tree SQLite DB (nodes, runs, iters, steps, events, messages — WAL-safe)
- session transcripts with per-request usage fields (append-only cost data)

The transcript harvester sits behind its own adapter module so future compaction-design
changes ripple through exactly one place (architect condition 3, verdict 8266A685).
Never parses conversational structure; reads only append-only per-request usage fields
written at response time.
"""
