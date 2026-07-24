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
| 42070 | commission (allocated, unbuilt) |
| 42080 / 42081 | authority grant / grant revocation (allocated, unbuilt) |

Addressable kinds sit in 381xx: 38110 node state pointer, 38150 template
pointer.

A new *family* takes the next decade; a new member of an existing family takes
the next units digit. Allocation is the architect's call, and every allocation
is collision-checked against `block/buzz` before its `docs/kinds/` entry is
written.

The last three are **allocated but unbuilt** — numbers and conditions are
fixed, the `docs/kinds/` entries are not yet written, and evergreen v1's kind
set stays closed at the nine above them. Two design constraints ride with
them. A **grant revocation is its own append-only event**, never a replaceable
update to the grant: a replaced grant would clobber the evidence that
authority once existed, the same reasoning that kept template versions out of
replaceable kind 10100. And a **commission (42070) names the authorizing
grant**, so the authorization chain is resolvable from the event alone.

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

## Querying: only single-letter tag filters are real

NIP-01 defines tag filters for **single-letter keys only** (`#e`, `#p`, `#d`,
`#h`, …). A multi-character key like `#branch` or `#template_name` is not part
of the spec, so a conformant relay does not reject it — it **silently ignores
it** and answers the remaining terms.

That is what makes this dangerous. The query succeeds. The events come back
signed and valid. They are simply the wrong ones, and nothing at the call site
indicates a filter was dropped. Measured against this tree's dev relay by
`evergreen`, a query filtered to one branch returned events spanning twelve
different branches — and zero from the branch actually requested; the filtered
and unfiltered queries returned identical result sets.

**The rules.**

1. Only single-letter `#<x>` keys go to the relay.
2. Any constraint expressible only as a multi-character tag is enforced in the
   client, after `event.verify()`, or it is not claimed.
3. Re-check even the spec-valid keys locally. Relay enforcement is an
   optimization, never an assumption (DESIGN.md §6 principle 5); this is that
   principle one level deeper.

**Do not "fix" the mock relay.** `tests/relay_mock.py` matches single-letter
keys only, which is *faithful* — it behaves exactly as a real relay does.
Making it honor multi-character keys would make every consumer's tests pass
against behavior no real relay exhibits, hiding this class of bug for every
node that reuses the mock. When a faithful double makes a bug invisible, the
defect is in the caller, never in the double. A shared test double may never be
more permissive than the strictest conformant real implementation.

**Why it is blocking, not cosmetic.** A surface labelled for one branch that
answers with every branch's events widens the audience of an aggregate — an
aggregates-up violation under §6.1, not merely a wrong result.

Writing a fixture that would have caught it takes two template names (or two
branches) in the same fixture set; a single-value fixture cannot express the
superset case at all.
