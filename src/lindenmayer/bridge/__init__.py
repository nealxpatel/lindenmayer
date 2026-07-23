"""Lindenmayer bridge: makes Fractal agent trees observable as signed Nostr events.

Reads Fractal's per-tree SQLite DB and session transcripts, translates to signed events,
and publishes through core's relay client. The bridge is a read-only host application
built on Fractal's observability hooks and documented extension surfaces.
"""
