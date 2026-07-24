---
name: l_system
desc: Lindenmayer shared node documentation and references.
tags: []
sources: []
created: 2026-07-23T12:40:09Z
updated: 2026-07-24T00:41:53Z
---

# l_system

[[bridge_implementation|bridge_implementation]]: Bridge node delivers Fractal observability as signed Nostr events.

[[event_kind_conventions|event_kind_conventions]]: How Lindenmayer allocates custom event kinds, and the rules every Buzz cross-post obeys.

[[evergreen_implementation|evergreen_implementation]]: The read plane -- a typed query surface over the signed log, the context-surface generator, and the history CLI.

[[fractal_read_adapters|fractal_read_adapters]]: Read-only adapters for accessing Fractal's SQLite database and transcript files.

[[node_operations|node_operations]]: Repo-specific fractal operating quirks every node hits (scope, transcripts, spawning).

[[registry_implementation|registry_implementation]]: Template registry for publishing, reading, and validating template versions as Nostr events.

[[relay_query_patterns|relay_query_patterns]]: How to filter relay queries correctly -- NIP-01 admits only single-letter tag filters, so multi-character constraints must be enforced client-side.

***
