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
  §2 identity and §3 registration wording aligned. NIP-OA is an `auth` TAG
  on ordinary events, not an event kind (§1/§2 worded accordingly; registry
  restatement at docs/kinds/nip-oa-attestation.md). Details in memory page
  relay_integration.
- §6 has **five** principles; the fifth (root directive 0FD60E31): relay
  enforcement is an optimization, never an assumption — client-side
  verification from the signed log is the security boundary. Its §4
  consequence is the "Extraction-pipeline requirements" paragraph
  (attestation-validity filtering done by the extractor itself; every corpus
  row labeled with attestation state at extraction time) — requirements, not
  guidance. Both cross-reference §1's layering rule; both trace to the
  decision-log row citing 0FD60E31.

## Core commissioning (first ply)

- `main.core` contract (tree/core/NODE.md, merged at 40a236c) countersigned
  **approve-with-conditions** (root request 8AFB1E8C, verdict reply 95D09C90;
  decision-log row in §9). Core starts on root's go after applying (or riding
  along via core's inbox) three conditions:
  - A: docs/kinds/ registry includes the NIP-OA schema restatement
    (nip-oa-attestation.md — nine files, not eight); contract's "never
    restated" means no re-derived custom kind, not no restatement doc.
    Upstream OA/AM/AO drafts pulled from block/buzz before entries written.
  - B: acceptable-degradation posture (aggregate rec. 3) documented in the
    library docs.
  - C: "escalated and acknowledged" completion gate reworded to gate on the
    escalation being sent; I commit to prompt acknowledgment when running.
- Boundary recorded: core owns `docs/kinds/` file contents inside my `docs/`
  scope; DESIGN.md and the rest of docs/ stay mine. Registry relocation from
  docs/research/relay-integration/kinds/ to docs/kinds/ approved.
- Collision-check escalation arrived (456E2D7B) and was resolved: all eight
  kinds clear vs block/buzz @ 06e3d82; ACK'd to core (F105F59A).

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

## Kind allocation & templates — closed

- §8 'custom kind allocation' and 'template registration mechanics' are
  CLOSED (decision-log rows cite 456E2D7B + root directive AF477673):
  42010/42020/42030/42040/42041/42050 regular, 38110/38150 addressable, all
  collision-free vs block/buzz @ 06e3d82 (crates/buzz-core/src/kind.rs — the
  platforms.md path cite is fixed), implemented in core, registry live at
  docs/kinds/. §3 now carries registry mechanics as current truth (42050
  append-only versions, 38150 pointer, inherit e-tag, eval anchor = version
  event id); §8 retains only compaction, retention, evals pillar, and
  history-grant mechanics.
- Dev-node template v1 (tree/templates/dev-node/, pinned 9574393):
  APPROVE-WITH-CONDITIONS (verdict 0773CC27). Condition: instance linkage
  line must carry the template pin ('dev-node v1 @ 9574393') so 42050's
  template_name/version/git_ref are mechanical. Non-blocking proposals:
  parameterize first-ply branch/parent lines; fable REVIEW pin on children
  is applied by the spawning parent. §3 notes the first live instance. Root
  instantiates the bridge node from this template after applying the
  condition.

## Bridge commissioning (first ply)

- `tree/bridge/NODE.md` (pinned ff957ad, first dev-node-template instantiation,
  linkage `dev-node v1 @ 9f147a3` — post-condition pin verified) countersigned
  **approve-with-conditions** (root request 9B395019, verdict reply 8266A685;
  decision-log row in §9; §3 pin cite refreshed 9574393→9f147a3 and first
  instantiation noted). Relay-as-cursor stateless resume APPROVED under §6.2.
  Conditions for root to apply: (1) restore contract-disagreement clause to
  Instructions; (2) deterministic event ids (content+created_at from Fractal
  source rows; replay tests assert on ids); (3) harvester isolated behind an
  adapter reading only append-only usage fields (contains §8 compaction
  coupling). Bridge starts on root's go after applying conditions.
