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
- **Core-log placement (root escalation D35D86E8, verdict 4038F1D1):** live
  Buzz interop showed the Buzz relay hard-rejects unknown kinds
  (ingest.rs:303 exhaustive match, no allowlist config) and enforces ±15-min
  created_at drift (MAX_TIMESTAMP_DRIFT_SECS=900, ingest.rs:1480) — both
  verified in ~/Code/buzz @ daeaf7c. Adopted option (a): core log lives on
  the **Lindenmayer relay** (own permissive strfry/khatru-class relay); Buzz
  is human surface only. §1 core bullet names the carrier + two carrier
  requirements (accepts custom kinds, accepts historical created_at); §1
  Buzz bullet records the rejections and cross-post rules (publish-time
  created_at, source ts + core event id in tags, dedup by reference); §6.2
  reworded; §8 gained relay-selection open question (NIP-29 support varies;
  khatru/relay29). Option (c) rejected (self-documenting kinds); option (b)
  — upstream kind-allowlist PR to block/buzz — endorsed non-blocking, never
  a dependency. Root to apply: bridge NODE.md publish target change; repo
  CLAUDE.md 'Buzz relay' source-of-truth line now stale.
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

## Evergreen commissioning (first ply, first dev-node v2 instance)

- `tree/evergreen/NODE.md` (pinned 2e73599, `dev-node v2 @ c6696b7`)
  countersigned **approve-with-conditions** (root request B92E616C, verdict
  06832636, decision-log row 430). Conditions: (1) add kind **38110** to
  deliverable 1 — the contract listed seven kinds and omitted the Node State
  Pointer, so the generator would replay 42010 chains for status the 381xx
  addressable range makes O(1); (2) deliverable 2 derives from deliverable 1
  (the signed-log query surface), never from Fractal's SQLite directly;
  (3) re-gate the live-demonstration requirement on the mock-relay fixture
  set, live run non-blocking.
- Two root deviations, both ruled on: scope `src,tests` **upheld against my
  own skeleton** (directory-granular scopes mean `docs/` would give a
  reviewed node commit rights over its own review bar — a §6.4 governance
  inversion); CLI-arg-path-under-test **confirmed but reassigned to dev-node
  v3**, since the failure recurred across two independent nodes (bridge,
  registry) and is therefore a template gap, not a per-contract risk.
- The privacy question root asked (is a committed context-surface fixture a
  §6.1 leak?) resolves **structurally, not by judgment**: 42020 is
  run-grained by schema, 42030 *is* the aggregate, and §7 already publishes
  this tree's transcripts — so the fixture discloses strictly less than
  `transcripts/`. That safety is load-bearing on condition 2; SQLite holds
  exactly the step detail the wire format excludes.

## Self-correction: "registration is live" over-implied reachability

§3's "registration is live" (from the model-policy retiering row) is true —
a relay was reachable when the operator ran the registry CLI for `0f8d0910` —
but I let it imply something false, that a *node* can reach a relay during
its run. It cannot: every publish path takes an operator-supplied `--relay`,
`CoreConfig.relay_url` has no default, no deployment TOML exists, and no
relay runs. §8 now records that the open relay question gates live
dogfooding tree-wide; the operational detail is in the shared wiki page
`node_operations` (section: no relay is reachable from inside a node run).

Pattern worth keeping: this is the same failure family as the compaction
premise, inverted. There the trap was accepting a child's *negative*
existence claim; here it was my own *positive* one. Both are premises, not
findings, and both propagated into the manifest before being checked.

## Self-correction: §8's "no relay is reachable" was false

The §8 relay bullet claimed no relay is reachable from inside a node run and
used that to justify a **tree-wide gating rule** (no node's completion may be
gated on live relay data). Measured during review: `nc -z localhost 7100`
succeeds, `8080` does not. A dev relay was answering the whole time the claim
stood — `docs/research/evergreen/inventory.md:94` records it holding 12 node
identities with live 42010/42020 events, and `evergreen`'s `6D3D3C19`
measurements were taken against it.

§8 now gates on **reproducibility, not reachability**: no `deploy/`, no
compose file, no deployment TOML, so the endpoint is operator ambient state a
node cannot discover — and the only relay default recorded in code
(`registry/cli.py:35`, `ws://localhost:8080`) points at a closed port, while
`bridge` requires `--relay` and `CoreConfig.relay_url` has no default. The
gating rule survives; its justification changed. Closing §8 means a checked-in
deployment plus one endpoint of record.

**This is the third instance of one failure family**, and naming it precisely
is the point: a false premise accepted from a child (compaction), my own
positive claim over-implying reachability ("registration is live"), and now an
*absence* claim asserted without measurement. Absence claims are the ones that
never get checked, because there is nothing to look at — and this one had
already hardened into a constraint other nodes were operating under. The
generalized rule: **any claim that something does not exist, is not reachable,
or is not recorded gets one command run against it before it enters the
manifest.** Each of the three cost one cheap command to check.

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
- **Never cite a decision-log row by number.** The log has no row ids, so
  "row 419" was only ever a *line* number, and every edit above it silently
  invalidates the citation — adding one row shifted the file by 13 lines and
  broke two such references at once. Cite the requesting message UUID
  instead (e.g. "the `core` commissioning review (request 8AFB1E8C)"): it is
  stable forever and resolves by search. Both pre-existing numeric citations
  have been converted.
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

## Registry commissioning (first ply)

- `tree/registry/NODE.md` (pinned 1c0409f, second dev-node-template
  instantiation, linkage `dev-node v1 @ 9f147a3`) countersigned
  **approve-with-conditions** (root request 41A80499, verdict reply 2C19A9A0;
  decision-log row in §9; §3 now records both instantiations). Relay-as-registry
  (no local index) APPROVED under §6.2, extending relay-as-cursor. Conditions:
  (1) instance-linkage association read-side only, terminates at the 42050
  version event id — no new kinds/wire artifacts/eval schema (reserves §8
  evals pillar); (2) reader orders version history by `version` tag,
  `created_at` informational (git timestamps non-monotonic); interpretive
  ruling logged, kind doc unchanged (core-owned). Registry starts on root's
  go after applying conditions.
