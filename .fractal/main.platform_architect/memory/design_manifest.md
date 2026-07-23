---
name: design_manifest
desc: State of docs/DESIGN.md ownership, audit findings, and open flags.
created: 2026-07-23T13:00:07Z
updated: 2026-07-23T13:00:07Z
---

# design_manifest

## Standing state

- This node owns DESIGN.md; the handrolled channel (root's operator editing it
  directly) is closed as of the commissioning decision-log entry. Design
  changes arrive in this node's inbox at priority 6; merges to main remain the
  root's approval gate.
- Status line reads "active manifest, owned and maintained by the architect".
- Structure: §0 what Lindenmayer is, §1 bridge, §2 identity, §3 node
  templates, §4 provenance/training + history grants, §5 evergreen node, §6
  design principles + shadow cost, §7 dev/demo strategy, §8 open questions,
  §9 decision log.
- §1 is now **Nostr-first two-layer** (root directive 5CD20B25, approved):
  Nostr core (standard NIPs + self-documented custom kinds, any-relay
  consumable) / Buzz layer (human surfaces, branch-as-room, buzz-protect).
  Draft-dependency rule: Buzz NIP drafts usable by core only
  schema-on-the-wire — NIP-OA attestation events core, relay-enforced
  revocation Buzz-layer; NIP-AM/AO schemas restated in our own kind docs.
  §2 identity and §3 registration wording aligned; §8 kind-allocation
  question reframed under the rule. Details in memory page
  relay_integration.
- §6 has **five** principles; the fifth (root directive 0FD60E31): relay
  enforcement is an optimization, never an assumption — client-side
  verification from the signed log is the security boundary. Its §4
  consequence is the "Extraction-pipeline requirements" paragraph
  (attestation-validity filtering done by the extractor itself; every corpus
  row labeled with attestation state at extraction time) — requirements, not
  guidance. Both cross-reference §1's layering rule; both trace to the
  decision-log row citing 0FD60E31.

## Audit findings

- Body cross-references verified correct: §4→§1, §4→§6.1, §4→§6.5, §5→§8,
  §3→§8, §6.5→§1, §6.5→research aggregate path.
- DESIGN.md and tree/platform-architect/NODE.md are consistent (governance
  veto, scope, principles, continuity open question all match).
- The entry-2 "(§7)"→"(§8)" citation typo (flagged in reply E37B3CF0) is
  fixed, authorized by root directive 08A7AF4B; correction noted in the
  commit message, no new log row.

## Platform parameters recorded

- Transcript publication: per-subgraph parameter (same family as governance
  mode), platform-wide default private-in-subgraph (§6.1); this dev tree
  explicitly opted in — hook-synced `transcripts/` are the demo data (§7).
  Decision-log row cites root directive 08A7AF4B.

## Conventions I follow when editing

- Every DESIGN.md change gets a decision-log row naming requester + verdict;
  every row traces to a radio message or root directive (cite the UUID).
- Manifest, not archive: current truth in body, history in log, bulk research
  in docs/research/.
- Radio-topology note lives in §5 (bounds evergreen visibility, refs §6.1) —
  chosen over §8 because it is current truth, not an open question.
