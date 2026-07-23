# Relay integration — research aggregate

Synthesis of the relay-integration research requested by the root (radio
5CD20B25) alongside the Nostr-first output-layering decision (DESIGN.md §1,
decision log). Two child studies feed this aggregate:

- **[event-kinds.md](event-kinds.md)** — the event-kind taxonomy: what
  Lindenmayer telemetry maps to standard NIPs vs needs custom kinds, and how
  custom kinds are documented for portability.
- **[degradation.md](degradation.md)** — the degradation analysis: what
  survives on a plain NIP-29 relay vs requires Buzz, and the
  identity/attestation story without NIP-OA enforcement.

This summary is the interface for the future `core` node's contract; the
detail lives in the two studies.

## Findings in brief

**1. The taxonomy is small and mostly standard.** Radio traffic rides
standard NIPs unchanged — messages are NIP-29 kind-9 group chat (with
Lindenmayer's `priority`/`subject` as ignorable extra tags), reactions are
NIP-25, saved-sets are NIP-51 addressable lists. Eight custom kinds cover
everything else, split into two blocks by semantics: `420xx` append-only
history (node lifecycle 42010, run accounting 42020, subgraph digest 42030,
approval request/verdict 42040/42041, template version 42050) and `381xx`
addressable pointers (node state 38110, template pointer 38150). Owner
attestation is deliberately *not* a Lindenmayer kind — it uses Buzz's NIP-OA
schema as-is, which DESIGN.md §1 already names core-usable
(schema-on-the-wire, not relay enforcement). All numbers are proposals
pending collision checks, not registrations.

**2. Privacy is designed into the taxonomy, not bolted on.** Run/step
accounting publishes one rolled-up event per run — never per step — and
ephemeral workers never author events at all; they surface only in their
persistent parent's subgraph digest. Step-level detail stays in Fractal's
SQLite. This makes "aggregates flow up, details stay in the subgraph"
(§6.1) a property of the wire format itself.

**3. Everything Lindenmayer *records* survives a plain relay; what degrades
is *enforcement*.** On a strfry/khatru-class relay speaking NIP-01/29/42,
all core flows store, version, and stay queryable/attestable. What's lost is
relay-side enforcement: approval-gated merges become records without gates,
identity revocation becomes a fact readers must check rather than an access
cutoff, and the packaged human surfaces (desktop app, directory, huddles)
disappear — though any NIP-29 client can still perform the same functions.

**4. The one degradation that is not cosmetic: private-group read gating.**
NIP-29's `private` flag ("only members can read") is spec-permissive —
relays *should* enforce it, and mainstream implementations do, but it is not
a protocol guarantee the way write-side moderation checks are. If a relay
stores the flag without enforcing it, the aggregates-up privacy default
silently degrades from a structural boundary to a client-side courtesy.
NIP-42 does not close the gap: it authenticates readers but leaves
authorization entirely to relay policy.

**5. Attestation without NIP-OA enforcement has a workable minimum.** The
bridge refuses to publish for revoked keys (closes new activity at the
source), and readers/extraction pipelines filter by attestation validity at
query time (bounds trust in stored history). This reproduces Buzz's outcome
with higher latency and procedural rather than structural guarantees.
Training-corpus safety (§4) is preserved provided the extraction pipeline
applies the attestation-validity filter itself instead of assuming the relay
did — and labels corpus rows with attestation state at extraction time.

## Recommendations for the core node's contract

- **Minimum relay contract:** assume NIP-01 + NIP-29 + NIP-42 and nothing
  more. NIP-34, Blossom, and Buzz custom-kind relay behavior are additive,
  never baseline.
- **Verify, don't infer, private-group enforcement:** treat relay-enforced
  `private` read gating as a per-deployment capability — a startup/config
  check or explicit operator attestation — and fail loud (refuse to mark a
  channel private) when it can't be confirmed. Buzz satisfies this by
  construction; "NIP-29 compliant" alone does not.
- **Ship with the acceptable degradations documented:** merge-gate
  enforcement is a bridge/process concern layered above the signed approval
  events; revocation latency under bridge-refusal + reader-filtering is
  documented, not hidden; human surfaces are pure UX with any NIP-29 client
  as substitute.
- **Custom kinds are self-documenting:** each carries the documentation
  convention from event-kinds.md §4 so any Nostr client can interpret them
  without Lindenmayer context; kind numbers get a collision check against
  Buzz's allocations before first publish (open in DESIGN.md §8).
