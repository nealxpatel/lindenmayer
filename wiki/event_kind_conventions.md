---
name: event_kind_conventions
desc: How Lindenmayer allocates custom event kinds, and the rules every Buzz cross-post obeys.
tags: []
sources: []
created: 2026-07-23T23:55:14Z
updated: 2026-07-23T23:55:14Z
---

# event_kind_conventions

Operational digest for nodes emitting or consuming Lindenmayer events. The
canonical statements live in `docs/DESIGN.md` §1 (allocation, cross-post
rules), §5.2 (compaction), and the decision log; per-kind schemas live in
`docs/kinds/`. This page is the short form — when it disagrees with
DESIGN.md, DESIGN.md wins.

## Kind allocation

Custom kinds are allocated **one decade per family** in the 420xx regular
block, with the units digit reserved for members of the same family:

| Kind | Family |
|---|---|
| 42010 | node lifecycle |
| 42020 | run accounting |
| 42030 | subgraph digest |
| 42040 / 42041 | approval request / verdict |
| 42050 | template version |
| 42060 | session compaction |

Addressable kinds sit in 381xx: 38110 node state pointer, 38150 template
pointer.

A new *family* takes the next decade; a new member of an existing family takes
the next units digit. Allocation is the architect's call, and every allocation
is collision-checked against `block/buzz` before its `docs/kinds/` entry is
written.

## Buzz cross-post rules

Cross-posts are derived views, never the record. Beyond that:

- **Audience invariant.** A cross-post may never widen the audience of its
  source event. Channel membership is the only access gate, so posting a
  subgraph event into a parent channel is a privacy widening. Kind 42030 is
  the sole kind eligible for a parent channel, because it *is* the upward
  aggregate.
- **Forward-only.** No historical backfill into Buzz. The relay's ±15-minute
  drift gate makes it infeasible, and re-issuing old events with fresh
  timestamps would misrepresent history. History lives on the Lindenmayer
  relay.
- **Tag elements are strings.** NIP-01 admits no embedded JSON objects in
  tags. Carry the source reference flat:

  ```
  ["e", "<source_id>", "", "lindenmayer-source"]
  ["source_kind", "42010"]
  ["source_created_at", "<unix>"]
  ```

  Dedup is by that core-event-id reference, not by id determinism (which holds
  only on the core path).

## Detecting compaction

**The harness already emits a marker — use it.** Transcripts carry an
append-only `system` record with a `compactMetadata` object:

```
trigger, preTokens, postTokens, durationMs,
cumulativeDroppedTokens, preservedSegment, preservedMessages
```

`preTokens`/`postTokens` are exactly the metrics kind 42060 reports. A
companion `user` record is flagged `isCompactSummary`. No upstream change is
needed, and nothing has to be inferred.

**Fallback, for transcripts without a marker.** Total prompt size grows across
a session and drops sharply at a compaction. Use the **three-term** form:

```
input_tokens + cache_read_input_tokens + cache_creation_input_tokens
```

Do **not** drop the third term. The two-term version tracks cache turnover,
not context: when the prompt cache expires, `cache_read` collapses toward zero
while `cache_creation` absorbs the prompt, producing a large false drop.
Measured across this tree's four largest sessions, two-term fired 4–6 times
per session; three-term fired twice, in exactly the two sessions carrying a
marker.

Every 42060 event records which signal produced it in a `detection` tag —
`harness-marker` (attested) or `usage-discontinuity` (inferred).

**Boundary.** The transcript adapter may read append-only structured metadata
records, but never conversational structure — and never the compact summary
body, which the harness does write to the transcript. 42060 carries the
summary's hash only.
