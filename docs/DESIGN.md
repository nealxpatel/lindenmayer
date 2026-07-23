# Lindenmayer — Platform Design Manifest

- **Owner:** `main.platform_architect` (see `tree/platform-architect/NODE.md`).
  Changes to this document land only through the architect; rejections are a
  veto by default.
- **Status:** active manifest, owned and maintained by the architect (adopted
  2026-07-23 from the root's bootstrap draft; the handrolled operator channel
  is closed — see decision log). Current truth lives in the body; history
  lives in the decision log; bulk research lives in `docs/research/`.

## 0. What Lindenmayer is

Lindenmayer is a control plane that lets humans govern subgraphs of Fractal
agent trees (plasma-ai/fractal) through Buzz (block/buzz), Block's Nostr-based
workspace — turning agent work into a versioned, evaluated, human-owned
workforce. Fractal and Buzz are external platforms this repo integrates; their
code does not live here. Lindenmayer adds no capabilities to Fractal nodes —
it makes existing Fractal primitives durable, identified, and observable
through Buzz.

## 1. The bridge (foundation layer)

- Implemented as a Fractal host application: consumes Fractal's `on_<event>`
  observability hooks, the per-tree SQLite DB, and JSON/CSV CLI outputs as
  read surfaces; steers only through Fractal's own contracts (radio, signals,
  step files, config). Never patches or forks Fractal.
- **Nostr-first output layering.** The primary integration target is the
  Nostr protocol, not Buzz per se. The bridge's output is two layers:
  - **Nostr core** — signed events any compliant relay can store and any
    standard Nostr client can read: standard NIPs where they fit (NIP-01
    wire format, NIP-29 group channels, NIP-34 git events), plus
    Lindenmayer's own custom kinds, self-documented for portability.
    Telemetry, radio aggregates, approval events, and template registration
    live here. The core log's carrier is the **Lindenmayer relay**: a
    permissive, standard Nostr relay (strfry/khatru-class) deployed with the
    tree, meeting the minimum relay contract (NIP-01 + NIP-29 + NIP-42, per
    the relay-integration aggregate) plus two carrier requirements the Buzz
    relay fails as deployed: it accepts Lindenmayer's custom kinds, and it
    accepts historical `created_at`, so backfill from Fractal source rows
    preserves deterministic event ids.
  - **Buzz layer** — Buzz-specific conveniences and relay-side behavior:
    the preferred human surface (desktop app, inboxes, agent directory),
    branch-as-room channel binding, buzz-protect merge enforcement. The
    Buzz relay is a human surface, not a core-log carrier: as deployed it
    hard-rejects kinds outside its own set and any `created_at` more than
    ±15 minutes from server time (both verified in block/buzz
    `crates/buzz-relay/src/handlers/ingest.rs` — the exhaustive kind gate
    and `MAX_TIMESTAMP_DRIFT_SECS` — @ daeaf7c). The bridge cross-posts
    human-facing messages into Buzz channels as Buzz-accepted kinds;
    cross-posts are derived views — publish-time `created_at`, with the
    source timestamp and the core event id carried in tags, deduplicated by
    that core-id reference — never the record. Losing this layer degrades
    experience, never history.
- **Draft-dependency rule.** The core may depend on a Buzz NIP draft only in
  its schema-on-the-wire aspect — signed, documented structure that any relay
  stores and any client can verify (NIP-OA attestation qualifies: an `auth`
  tag carried on ordinary signed events, not a distinct event kind). Any
  dependency on Buzz relay-side enforcement or behavior is Buzz-layer. Where core kinds align with drafts (NIP-AM / NIP-AO metrics),
  the schemas are restated in Lindenmayer's own kind documentation so they
  survive draft churn.
- Maps tree structure onto channels: Fractal nodes are git branches →
  subgraphs bind to NIP-29 group channels ("branch as room" is the
  Buzz-layer binding of the same idea to hosted git); channel membership is
  the only access gate.
- Node identity via NIP-OA owner attestation: each node's keypair is attested
  by its responsible human (an `auth` tag — owner pubkey, conditions, BIP340
  signature — attachable to any event; restated in
  `docs/kinds/nip-oa-attestation.md`). The attestation chain is core
  (verifiable anywhere); relay-enforced instant revocation — remove the
  human, the subgraph loses access — is Buzz-layer (see §2).
- Fractal `requires_approval` steps surface as signed approval events (core);
  enforcement of approval-gated merges via buzz-protect is Buzz-layer.

## 2. Identity (persistent nodes)

Fractal provides the graphs and subgraphs; connecting a node to the relay is
what gives it an identity (an npub, attested per NIP-OA — the attestation
tag chain is core per §1's layering; a plain relay keeps the chain
verifiable, while instant enforcement of revocation is Buzz-layer). Not all
nodes need one —
only the persistent nodes central to executing work. Conceptually, persistent
nodes are like the "sub-agents" of coding harnesses: named, durable roles with
track records. Ephemeral worker nodes stay anonymous inside their subgraph;
their work reaches the record only as the aggregates their persistent parent
signs.

## 3. Node Templates (the improvable asset)

The unit of improvement is the **Node Template**, not the node instance. A
template contains system prompts, skills, files, and references, and defines
the context available to the node via tool calls. Templates are registered in
the registry as signed events (Nostr-core kinds per §1), so every template is versioned,
attributable, and diffable; instances record which template version spawned
them, and evals attach to template versions. That linkage — instance → template
version → eval history — is what makes the workforce "versioned and
evaluated" rather than a pile of one-off prompts.

Registration mechanics are specified in the kind registry (`docs/kinds/`):
kind 42050 (template version, append-only regular events — full history
preserved so versions stay diffable; inheritance via `e`-tag with `inherit`
marker) and kind 38150 (template pointer, addressable). What an eval
attaches to is the 42050 version event id; the evals pillar itself remains
open (§8).

The first live template instance exists: `tree/templates/dev-node/` (v1,
pinned at commit 9f147a3 — the pin-bearing revision that applied the
architect's linkage condition) packages the proven dev-node shape —
decomposition doctrine, haiku-develop/fable-review model policy,
architect-consultation covenant — hand-rolled in git until `registry` holds
template versions as signed 42050 events. Instances record the template
name, version, and template commit pin, which map onto 42050's
`template_name`/`version`/`git_ref` tags. Two instantiations exist, both
carrying the linkage line `dev-node v1 @ 9f147a3` and commissioning-reviewed
per the decision log: the bridge node contract (`tree/bridge/NODE.md`) and
the registry node contract (`tree/registry/NODE.md`) — the latter is the
node that will hold these template versions as signed 42050 events.
Template changes are key-component changes: architect review, version bump,
decision-log entry.

## 4. Provenance as a training asset

Signed provenance is what closes the improvement loop on templates: the event
log is not just an audit surface, it is a training corpus with labels built
in. The provenance of functionality is valuable for fine-tuning / training in
at least four distinct ways:

1. **Filtering / labeling.** Train on approved work only, or weight samples
   by acceptance — approval events (§1) are the labels.
2. **Preference pairs.** Rejection → revision → acceptance chains, already
   recorded as threaded signed events, yield natural preference pairs for
   DPO-style training.
3. **Outcome / context conditioning.** The model learns what distinguishes
   trajectories that get approved, because each trajectory carries its full
   context: template version, subgraph, reviewer, verdict.
4. **Auditable trails.** Debugging trained behavior is tractable with
   guarantees on versioning — any output traces to the template version and
   signed history that produced it.

This is why identity and signing are load-bearing rather than decorative:
unsigned telemetry can be dashboarded, but only attested, versioned history
can be safely trained on.

**Extraction-pipeline requirements.** The verification burden of §6.5 is not
uniform across consumers, and it is heaviest here. An interactive client
that briefly trusts a revoked agent shows a stale message; an extraction
pipeline that trusts the relay bakes unattested trajectories into model
weights. Two requirements follow. The extraction pipeline applies
attestation-validity filtering itself — it never assumes the relay enforced
revocation or membership. And every corpus row is labeled with its author's
attestation state at extraction time, so downstream training can filter or
weight on it.

**History access grants.** Training use of history is consent-gated, and the
consent mechanism is the platform's own idiom: a human grants time-limited
access to their history — to a node or to another human — as a **signed,
revocable, expiring event**. Consent thereby has the same provenance as
everything else: who granted what to whom, for which purpose, over which
window, and whether it was revoked are all facts in the event log, not rows
in a side policy store. Grants exist to facilitate fine-tuning a model for a
given task or project; the training itself runs on hosted inference/tuning
infra (Baseten/Fireworks-type) and is future development. Extraction
pipelines honor grants and their expiry/revocation, respecting §6.1
(mechanics open, §8).

## 5. The Evergreen Node

The **Evergreen Node** is the root node a human uses to manage their subgraph:
their durable, standing context environment. From it the human can:

- commission trees on the fly,
- steer subgraphs (radio, signals, live contract edits),
- review approvals,
- query their own history.

What the evergreen node sees is bounded by the platform's own wiring: radio
subscriptions are one hop, parent to direct child, so a subgraph's details
reach the evergreen root only as the aggregates each persistent child chooses
to publish upward. The aggregates-up privacy default (§6.1) is thereby
structurally enforced by the messaging topology itself, not policed after the
fact.

The first Evergreen Node is handrolled at `tree/root/CONTEXT.md` and is the
living prototype: whatever that file needs to be is what Lindenmayer must
eventually generate and maintain automatically.

Evergreen sessions raise the continuity problem: long-lived sessions compact,
and a compaction is a derived view that must keep a pointer to its source —
each compacted summary should map to the run/iter/step it covers so raw
context stays traceable (open question, §8).

## 6. Design principles

1. **Privacy-preserving defaults.** Human employees' full potential on this
   platform is only unlocked with a privacy-first approach; the goal is a
   collaboration platform for humans and AI as one integrated organizational
   graph. No arbitrary search of histories: access follows the graph —
   aggregates flow up, details stay in the subgraph. Privacy is a default,
   not a feature. Whether a subgraph publishes its raw node-session
   transcripts is a per-subgraph platform parameter (same family as the
   governance-mode parameter, §6.4); the platform-wide default is
   private-in-subgraph.
2. **No new storage systems.** The signed event log is the history. Retention
   is relay policy, per channel. Source-of-truth data stays in Fractal's
   SQLite and the signed event log on the Lindenmayer relay (§1; the Buzz
   relay carries the human workspace, never the record); parquet files in
   `data/` are snapshot exports for local review (duckdb), never sources of
   truth.
3. **Never patch or fork Fractal.** Integrate only through its extension
   surfaces; add no capabilities to Fractal nodes.
4. **Human governance is explicit and traceable.** Design review is a veto by
   default (a platform parameter); disagreements resolve as recorded
   conversation, never silent override.
5. **Relay enforcement is an optimization, never an assumption.** Client-side
   verification from the signed log is the security boundary. Buzz's
   relay-side enforcement — instant revocation cutoff, approval-gated
   merges, membership-checked writes, private-group read gating — is
   defense-in-depth that makes enforcement cheap when Buzz is deployed
   alongside, but it is Buzz-layer under §1's layering rule, and no client,
   bridge, or consumer may reason from it. Every consumer verifies from the
   signed log alone: attestation chains are checked before an author is
   trusted, approvals are counted before a merge is treated as approved,
   revoked keys are filtered at read time, and private-group read gating is
   treated as unverified until the deployment proves it. (Detail and the
   minimum relay contract: the relay-integration research aggregate,
   `docs/research/relay-integration/README.md`.)

### Shadow cost

All dollar figures in this project are *shadow costs*: real, server-reported
token counts priced at public API rates (Fractal's LiteLLM pricing table),
while execution actually runs on a Claude Max subscription. Nothing was
billed at these prices.

- Token counts are ground truth (reported by the API in stream events, never
  estimated locally). Dollar figures are derived, notional, API-equivalent
  prices.
- Fractal's budget primitives (`max_cost`, reserve mode, cascading finish)
  operate on shadow cost and remain fully functional as steering and safety
  mechanisms — a budget cap is a real cap on work, even if the dollars are
  notional.
- Shadow cost is the right unit for the control plane's analytics: it is
  comparable across nodes, templates, models, and time, independent of how
  any given org pays (subscription, API, or enterprise agreement).
- The binding constraint on subscription execution is not dollars but rate
  windows; throttling events are recorded and reported separately from cost.
- Every exported dataset (parquet snapshots, demo dashboards) labels cost
  columns as shadow cost. No figure is presented as actual spend.

## 7. Development & demo strategy

- Developed by a Fractal tree from day one; the demo observes the tree that
  builds Lindenmayer, so dashboards show real subgraphs, merge-acceptance,
  and cost data.
- This dev tree is explicitly opted in to transcript publication (the
  per-subgraph parameter in §6.1): hook-synced node-session transcripts
  (`transcripts/`) are committed and published — for this tree they are the
  demo data. The platform-wide default remains private-in-subgraph.
- Decomposition principles for the dev tree: nodes own mergeable,
  directory-scoped artifacts; shared contracts land before parallel children
  spawn; the tree mirrors intended module boundaries; plan one ply and let
  nodes decide their own children; hand-authored Completion Requirements per
  NODE.md prefigure the evals pillar.
- **First ply:** `core` (event kinds, relay client, config — merges first),
  `bridge`, `registry`, `evergreen`, `evals` (spawned late; depends on bridge
  events).
- Full autonomous self-management is explicitly out of scope; named as
  endgame only.

## 8. Open questions

- **Compaction-to-task mapping.** How evergreen-session compactions are
  recorded as events mapping summary → run/iter/step → raw transcript.
  (Raised by root, 2026-07-23.)
- **Retention policy defaults.** What per-channel relay retention ships as
  the privacy-preserving default.
- **Evals pillar.** Sketched only via hand-authored Completion Requirements;
  needs its own design pass once bridge events exist.
- **Lindenmayer relay selection & deployment.** Which permissive relay
  implementation carries the core log (strfry/khatru-class), given §1's
  carrier requirements — custom kinds accepted, historical `created_at`
  accepted, NIP-29 groups and NIP-42 auth available (support varies across
  implementations; NIP-29 often lives in add-ons like relay29) — and what
  its deployment and retention posture is. (Raised by root escalation,
  2026-07-23.)
- **History-grant mechanics.** The consent model is decided — a signed,
  revocable, expiring grant event (§4) — but its mechanics are open: kind
  number and tag schema (Nostr has prior art in NIP-40 expiration and NIP-09
  deletion/revocation), grant granularity (whole history vs. per-channel vs.
  per-subgraph vs. per-time-range), how extraction pipelines enforce expiry
  and revocation, what revocation means for training runs already in flight,
  and integration with hosted tuning infra (Baseten/Fireworks-type).

## 9. Decision log

| Date | Decision | Requested by | Resolution |
|---|---|---|---|
| 2026-07-23 | Governance mode: architect rejection is a veto by default; a rejection forces the human to re-examine the principle at stake and adjust context/contracts in recorded conversation on the architect's node. Softer modes (advisory, recorded override) are per-subgraph platform parameters. | root | Adopted; encoded in `tree/root/CONTEXT.md` and `tree/platform-architect/NODE.md`. |
| 2026-07-23 | Evergreen continuity: compactions must map back to the task (run/iter/step) they summarize, as a trace to raw context. | root | Accepted as open design question (§8); noted in the architect's contract. |
| 2026-07-23 | This manifest bootstrapped from the root's design sketch (bridge, identity, templates, evergreen node, principles, dev/demo strategy). | root | Adopted as draft; §3 registration sentence completed by inference, pending root review. |
| 2026-07-23 | Provenance is a training asset (§4): the signed event log doubles as a labeled training corpus — filtering by acceptance, preference pairs from rejection→revision→acceptance chains, outcome/context conditioning, and versioned audit trails for debugging trained behavior. | root | Adopted; training extraction & consent added as open question (§8). |
| 2026-07-23 | History access grants (§4): humans grant time-limited history access — to a node or another human — for task/project fine-tuning, modeled as a signed, revocable, expiring event so consent has the same provenance as everything else. Hosted tuning infra (Baseten/Fireworks-type) is future development. | root | Adopted; resolves the consent-model half of the prior open question; grant mechanics remain open (§8). |
| 2026-07-23 | Shadow cost (§6): all dollar figures are notional API-equivalent prices over ground-truth token counts; execution runs on a Claude Max subscription. Budget primitives operate on shadow cost; rate windows are the real constraint and are reported separately; exports label cost columns as shadow cost. | root | Adopted; added as a Design principles subsection. |
| 2026-07-23 | Commissioning of `main.platform_architect`: this node now owns DESIGN.md and associated docs. The handrolled channel (the root's operator editing DESIGN.md directly) is closed; future design changes route through this node's inbox (priority 6) for review; merges to main remain the root's approval gate. Status line updated to reflect active ownership. All prior entries in this log are handrolled bootstrap history, audited and left unedited. | root (directive A2C8C8C7) | Adopted; first architect-committed change to this manifest. |
| 2026-07-23 | Radio's one-hop subscription topology (parent subscribes only to direct children's outboxes) structurally enforces the aggregates-up privacy principle (§6.1): the platform's own wiring implements the design principle. Noted in §5, where it bounds evergreen-node visibility. | root (directive A2C8C8C7) | Adopted; placement in §5 per architect's judgment from the root's offered §5/§8. |
| 2026-07-23 | Node-session transcripts as published telemetry: whether a subgraph publishes its raw node-session transcripts is a per-subgraph platform parameter (same family as governance mode); the platform-wide default is private-in-subgraph, consistent with §6.1. This dev tree is explicitly opted in — hook-synced transcripts are committed and published as the demo data. | root (directive 08A7AF4B) | Adopted, no veto — the private default is §6.1 applied to transcripts. Parameter + default recorded in §6.1; dev-tree opt-in recorded in §7. |
| 2026-07-23 | Nostr-first output layering (§1): standard Nostr — not Buzz per se — is the bridge's primary integration target; core telemetry is consumable by any compliant relay and client (standard NIPs plus self-documented custom kinds), with Buzz-specific kinds and relay behavior a layer on top. Draft-dependency rule: the core may use a Buzz NIP draft only as schema-on-the-wire (NIP-OA attestation events qualify); relay-enforced revocation, branch-as-room, and buzz-protect are Buzz-layer; NIP-AM/AO alignment is restated in Lindenmayer's own kind docs. | root (directive 5CD20B25) | Approved, no veto — strengthens §6.2 (an event log readable by one v0.4.x product is a weaker source of truth) and hedges Buzz churn at no capability cost. §1 rewritten as two layers; §2 identity and §3 registration wording aligned; §8 kind-allocation question reframed under the rule; relay-integration research children spawned to detail the kind taxonomy and plain-relay degradation. |
| 2026-07-23 | Security boundary (§6.5): relay enforcement is an optimization, never an assumption — client-side verification from the signed log is the security boundary; Buzz relay-side enforcement is defense-in-depth no client, bridge, or consumer may reason from. Training-pipeline consequence (§4): the extraction pipeline applies attestation-validity filtering itself and labels every corpus row with its author's attestation state at extraction time — stated requirements, not guidance. | root (directive 0FD60E31) | Adopted — elevates the relay-integration research recommendation (aggregate finding 5, `docs/research/relay-integration/README.md`) from research advice to platform principle. §6 principle 5 added; §4 "Extraction-pipeline requirements" paragraph recorded; both cross-reference §1's layering rule. |
| 2026-07-23 | Commissioning review of the first-ply `core` node contract (`tree/core/NODE.md`, merged at 40a236c), reviewed against the relay-integration research recommendations (`docs/research/relay-integration/`) and §§1, 4, 6, 7. | root (directive 8AFB1E8C) | **Approve-with-conditions** — the contract faithfully carries the minimum relay contract (NIP-01+29+42 and nothing more), verify-don't-infer private-group gating (fail loud), wire-format privacy (§6.1: per-run rollups, ephemeral workers author no events), the §6.5 verification module with §4 extraction-time attestation labeling, §6.2 in config, and collision-check escalation reserved to the architect. Three conditions: (1) the `docs/kinds/` registry includes the NIP-OA schema restatement (`nip-oa-attestation.md`, per event-kinds.md §1.7/§3/§4) — the contract's "never restated" is read as "no re-derived custom kind," not "no restatement doc" — with the upstream NIP-OA/AM/AO drafts pulled from `block/buzz` before those entries are written; nine registry files, not eight. (2) The acceptable-degradation posture (aggregate recommendation 3: merge-gate enforcement as a process concern above the signed events, revocation latency under bridge-refusal + reader-filtering, human surfaces substitutable) is documented in the library's own docs. (3) The completion gate "escalated to the architect and acknowledged" is reworded to gate on the escalation being sent — an acknowledgment only the architect can issue risks stranding a done node `exited`; the architect commits to prompt acknowledgment whenever running. Registry relocation from the research's proposed `docs/research/relay-integration/kinds/` to `docs/kinds/` is approved — implementation-grade spec belongs outside `research/`. Shared-scope boundary recorded: `core` owns `docs/kinds/` file contents; `DESIGN.md` and the rest of `docs/` stay architect-owned. Contract-text edits are proposals to the root (tree/ is the root's to edit). |
| 2026-07-23 | Custom kind allocation (§8) closed: all eight Lindenmayer kinds — regular 42010/42020/42030/42040/42041/42050, addressable 38110/38150 — verified collision-free against block/buzz @ 06e3d82 (`crates/buzz-core/src/kind.rs`; nearest Buzz neighbor 42000, nothing in 381xx; NIP drafts claim 44200 and ephemeral 24200, no overlap), implemented in `core`, and self-documented in the live registry `docs/kinds/`. Template-registration mechanics closed with it (42050 append-only versions, 38150 pointer, `inherit` e-tag; eval anchor = version event id) — now current truth in §3; only the evals pillar itself stays open. Upstream correction adopted: NIP-OA is an `auth` tag attachable to any event, not an event kind — no kind number exists to collide, and §1/§2 wording plus the `platforms.md` kind.rs path cite are corrected accordingly. | main.core (collision check 456E2D7B); root (directive AF477673) | Confirmed — allocation stands as proposed, no veto. §8 bullets removed; §3 records registry mechanics as decided. |
| 2026-07-23 | Review of the dev-node template (`tree/templates/dev-node/`, v1, pinned 9574393) — the first live instance of the §3 Node Template concept, hand-rolled in git until `registry` holds template versions as signed events. Reviewed for §3 fidelity (instance→template-version linkage), consultation-trigger calibration, and consistency with the manifest and prior countersigns. | root (directive AF477673) | **Approve-with-conditions** — adopted as the standard shape for future dev nodes; §3 notes the instance. Condition: the recorded linkage line must carry the template commit pin (e.g. `template: dev-node v1 @ 9574393`), not just name+version — a future kind-42050 event needs `template_name`/`version`/`git_ref`, and "this file" resolves to a `git_ref` only by archaeology; with the pin, migration to signed registration is mechanical. Trigger set judged correctly calibrated: covers exactly the architect's remit (key components, principle deviations incl. §6.2 storage and §6.5 verification weakening, new runtime deps) with a decided-matters catch-all, while "STOP only the affected path", "consult on architecture, not style", and SENT-not-acknowledged escalations (honoring the core-commissioning condition on completion gates) bound the bottleneck risk. Non-blocking proposals to root: parameterize the hardcoded first-ply `branch`/`parent` lines before instantiating deeper persistent nodes, and clarify that the fable REVIEW-step pin on a child is applied by the spawning parent (a child cannot edit its own immutable seed). Template text remains the root's to edit. |
| 2026-07-23 | Commissioning review of the `bridge` node contract (`tree/bridge/NODE.md`, pinned ff957ad) — the first instantiation of dev-node template v1, reviewed for template fidelity, design fidelity (§1, §6.1, §6.2, §6.5, §4), buildability under haiku economics, and coupling with §8's compaction question. Includes the explicit §6.2 ruling requested on deliverable 4's stateless-resume design: **the relay is the cursor** — on startup the bridge queries its own latest published events per node and resumes from there; no local state files. | root (request 9B395019) | **Approve-with-conditions** — template fidelity verified (linkage line `dev-node v1 @ 9f147a3` resolves to the post-condition template; covenant/model-policy/doctrine operative content intact; the added "never write to Fractal's SQLite" and new-dep-is-automatically-a-consultation clauses are welcome strengthenings). Relay-as-cursor is APPROVED as the §6.2-clean answer to bridge state: the relay is already a source of truth, a local cursor file would be a new storage system, and writing position into Fractal's SQLite would breach the read-only boundary; crash-safety falls out for free. Three conditions: (1) restore the template's contract-disagreement clause (radio the root, priority 6, instead of guessing) to the Instructions opening — the escape hatch matters most for a haiku executor; (2) deliverable 4's no-duplicates acceptance must pin event-id determinism — event content and `created_at` derive from Fractal source rows (source timestamps, never wall clock), so a replay after cursor regression reproduces identical event ids and the idempotent-replay tests assert on ids; (3) deliverable 1's transcript usage harvester reads only append-only per-request usage fields behind its own adapter, never parsing conversational structure — transcript schema is harness-owned and unstable, and §8's open compaction-to-task mapping will land in the same territory (coupling flagged, non-blocking under this isolation). Non-blocking notes: cursor startup queries fit the minimum relay contract's NIP-01 REQ surface (author+kind+limit); relay retention pruning degrades benignly given condition 2 (re-publish is id-idempotent). Caps judged sane: $20/10 iters haiku against core's observed $13.36 for a comparable half-charter, with the ×1.3 child-pricing rule protecting the split. Contract-text edits are proposals to the root (tree/ is the root's to edit). |
| 2026-07-23 | Commissioning review of the `registry` node contract (`tree/registry/NODE.md`, pinned 1c0409f) — the second instantiation of dev-node template v1 (@ 9f147a3), reviewed for template fidelity, design fidelity (§3 registry mechanics, §6.1, §6.2, §6.5, deterministic-id precedent), buildability under haiku economics, and coupling with the reserved evals pillar (§8). Includes the explicit §6.2 ruling requested on the no-local-index posture: **the relay is the registry** — reads reconstruct template history from 42050/38150 queries; no local index files. | root (request 41A80499) | **Approve-with-conditions** (verdict 2C19A9A0) — template fidelity verified: linkage pin `dev-node v1 @ 9f147a3` resolves to the post-condition template; contract-disagreement clause present in the Instructions opening (the bridge condition honored proactively); covenant/model-policy/doctrine operative content intact, with welcome strengthenings ("the relay IS the registry; no local index files", kind-docs-are-decided-matters, registry-level-dep-is-automatically-a-consultation, and the §6.1 adaptation: templates publish openly as shared assets, instance linkage leaks nothing beyond 42010/42030). Relay-as-registry is APPROVED as §6.2-clean in both directions, extending the bridge's relay-as-cursor precedent: 42050 content stays thin (`git_ref` points at the artifact — no second copy of template content) and 38150 pointer loss degrades to replaying 42050 history, never data loss. Two conditions: (1) evals boundary — deliverable 3's instance→template-version association is read-side only and terminates at the 42050 version event id; no new event kinds, no wire-visible association artifacts, no eval-shaped schema — anything wire-visible for evals belongs to the open §8 pillar and is automatically an architect consultation. (2) reader ordering robustness — `created_at` derives from git commit timestamps, which are not guaranteed monotonic, so version-history reconstruction orders by the `version` tag with `created_at` informational; interpretive ruling: the 42050 doc's "ordered by `created_at`" reads as descriptive of the common case, not normative for readers (kind-doc text is core-owned and unchanged). Non-blocking: the omitted self-pin in the Instructions is unresolvable at authoring time — the pin of record is 1c0409f via the request and this row, consistent with bridge practice; the E2E dogfood (register `dev-node v1 @ 9f147a3` against a mock relay) is achievable by reusing the bridge's in-process NIP-01 mock-relay test infra, and run live doubles as the platform's first real template registration (§7 dogfooding); caps sane ($15/10 iters haiku for four deliverables reusing core + bridge infra, vs bridge's $20/10 for five). Contract-text edits are proposals to the root (tree/ is the root's to edit). |
| 2026-07-23 | Core-log placement (§1): the Lindenmayer core event log lives on its own permissive relay (strfry/khatru-class) — the **Lindenmayer relay** — and the Buzz relay demotes from assumed core-log carrier to human surface. Trigger: first live bridge-to-Buzz run showed the Buzz relay hard-rejects unknown kinds (exhaustive `required_scope_for_kind` match, no config escape) and enforces ±15-min `created_at` drift (`MAX_TIMESTAMP_DRIFT_SECS=900`) — both findings independently verified by the architect in block/buzz `crates/buzz-relay/src/handlers/ingest.rs` @ daeaf7c. | root (escalation D35D86E8) | **Adopted — option (a)** of the root's three. The Nostr-first layering absorbs this cleanly: §1 already defined the core as "signed events any compliant relay can store"; the live finding is that the Buzz relay is not a compliant carrier for Lindenmayer kinds, so the core log gets a carrier that is. Not a §6.2 violation: the signed event log was always the history and a relay always its carrier — what changed is which deployment runs the relay, not what stores truth; §6.2 wording updated to name the Lindenmayer relay. Option (c) — re-encoding telemetry inside Buzz-accepted kinds — REJECTED: it violates the self-documenting-kind design and §1's core-layer definition (events would be readable only by deciphering a private embedding convention). Option (b) — upstream a configurable kind-allowlist to block/buzz — ENDORSED as a non-blocking parallel track: a legitimate open-source contribution, not a fork under §6.3, but no design surface may depend on its acceptance; if it lands, the Buzz relay becomes *a* compliant carrier, never *the* carrier. New §8 open question records relay selection/deployment. Contract consequence (root to apply; tree/ is the root's): the bridge's publish target becomes the Lindenmayer relay, with Buzz cross-posting a separate derived path. |
| 2026-07-23 | Timestamp policy and id determinism restated per publish path (§1): core-log events on the Lindenmayer relay keep bridge condition 2 unchanged — content and `created_at` derive from Fractal source rows, ids deterministic, backfill id-idempotent (the carrier requirement "accepts historical `created_at`" exists precisely so this holds). Buzz-bound cross-posts are derived views, not the record: `created_at` is publish time (satisfying Buzz's drift window), the source timestamp and the core event id ride in tags, and idempotency is by reference — the bridge dedups by querying for an existing cross-post citing that core event id (relay-as-cursor extended), not by id determinism. | root (escalation D35D86E8) | Adopted; encoded in §1's Buzz-layer bullet. Bridge condition 2 (verdict 8266A685) needs no restating for the core path; the by-reference rule is the id-determinism story for any Buzz-bound path. |
