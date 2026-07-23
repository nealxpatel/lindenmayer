---
name: l_system
desc: Lindenmayer bridge node documentation and shared references.
tags: []
sources: []
created: 2026-07-23T12:40:09Z
updated: 2026-07-23T20:24:17Z
---

# l_system

[[bridge_implementation|bridge_implementation]]: Bridge node delivers Fractal observability as signed Nostr events

[[fractal_read_adapters|fractal_read_adapters]]: Read-only adapters for accessing Fractal's SQLite database and transcript files

[[node_operations|node_operations]]: Repo-specific fractal operating quirks every node hits (scope, transcripts, spawning).

***

Lindenmayer is a control plane that makes Fractal agent trees observable through signed Nostr events published to Buzz, turning agent work into versioned, evaluated, human-owned records.

## Key References

[[bridge_implementation|bridge_implementation]]: Bridge node implementation — translates Fractal operations to signed Nostr events.

[[fractal_read_adapters|fractal_read_adapters]]: Read-only adapters for accessing Fractal's SQLite database and transcript files.

[[node_operations|node_operations]]: Repo-specific fractal operating quirks every node hits (scope, transcripts, spawning).
