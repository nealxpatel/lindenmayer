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
    live here. Custom kinds are allocated one decade per family in the 420xx
    regular block — 42010 lifecycle, 42020 accounting, 42030 digest, 42040/1
    approval, 42050 template, 42060 compaction — with the units digit
    reserved for members of the same family, so a new family takes the next
    decade and allocation stays mechanical. Every allocation is
    collision-checked against `block/buzz` before its registry entry is
    written. The core log's carrier is the **Lindenmayer relay**: a
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

    **Cross-post rules (v1).** Two invariants bind every cross-post:

    - *Audience invariant.* A cross-post may never widen the audience of its
      source event. Channel membership is the only access gate, so posting a
      subgraph event into a parent channel is a privacy widening (§6.1).
      Kind 42030 is the sole kind eligible for a parent channel, because it
      *is* the upward aggregate.
    - *Forward-only.* Buzz receives cross-posts in real time and never
      backfill: the ±15-min drift gate makes historical posting infeasible,
      and re-issuing old events with fresh timestamps would misrepresent
      history. History lives on the Lindenmayer relay.

    Tag elements are strings (NIP-01), so the source reference is carried
    flat, never as an embedded JSON object:
    `["e", "<source_id>", "", "lindenmayer-source"]`, `["source_kind", "…"]`,
    `["source_created_at", "<unix>"]`.

    The v1 set: 42010 and 42020 → `KIND_STREAM_MESSAGE` (9) in the subgraph
    channel; 42040/42041 → stream message in an approvals-inbox NIP-29 group;
    42030 → parent channel where the subgraph publishes upward; 38150 and
    42050 not surfaced (see decision log — template versions must not be
    published as replaceable agent-profile events).
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

The first live template exists: `tree/templates/dev-node/` packages the proven
dev-node shape — decomposition doctrine, model policy, architect-consultation
covenant. Instances record the template name, version, and template commit
pin, which map onto 42050's `template_name`/`version`/`git_ref` tags. Two
instantiations exist, both commissioning-reviewed per the decision log: the
bridge node contract (`tree/bridge/NODE.md`) and the registry node contract
(`tree/registry/NODE.md`).

**Registration is live, not future.** `registry` holds template versions as
signed 42050 events today: dev-node **v2** is registered (version event
`0f8d0910`, pin `c6696b7`) — the registry's first real version bump, read back
and verified alongside v1. Hand-rolled git pinning was the interim; the signed
registry is now the record. Template changes remain key-component changes:
architect review, version bump, decision-log entry.

**Model policy is a template parameter, not a platform constant.** What the
template fixes is the *shape*: the orchestrator writes precise work orders, a
cheaper tier executes them, a stronger tier reviews the result. Which tiers
fill those slots is tunable and has already been retuned once (see decision
log). Current assignment: orchestration and review on the stronger tier,
development on the cheaper one. Surfaces that display the policy must read the
live assignment rather than restate it — a restated tier table goes stale
silently, and has.

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

### 5.1 What evergreen is at v1

**Evergreen v1 is the read plane; Fractal's own CLI remains the write plane.**
v1 ships two things and no write path: a query surface over the signed log,
and a generator/maintainer of the standing context surface.

The write-side gaps are real but they are not ours to fill. Radio send,
signals, live `NODE.md` edits, and node spawn are Fractal capabilities that
already exist and work; wrapping them would add a second control path with no
new capability, and an orchestration layer over Fractal's spawn API drifts
straight at §6.3. That signal routing is "Fractal CLI only" is not a gap —
it is the boundary holding. The read side is the opposite case: most of what
the prototype needs is reconstructable from the signed log, and none of it has
a query surface today.

| §5 capability | v1 ships (read) | Stays Fractal CLI (write) |
|---|---|---|
| Commission trees | template catalog: versions, history, instance linkage | the spawn itself |
| Steer subgraphs | situational awareness: aggregates, budgets, pending gates | radio send, signals, live edits |
| Review approvals | the queue: 42040 pending, 42041 verdicts | the verdict (a radio reply) |
| Query own history | owned fully — this *is* the capability | — |

The generated context surface is a composite: a human-authored preamble
(mission, phase, non-negotiables, governance mode, pointers) plus a generated
situational block derived from queries. That is what the handrolled prototype
already is, minus the hand maintenance.

v1 holds no local index — it reconstructs from the relay and Fractal's SQLite
on demand, extending the relay-as-cursor (bridge) and relay-as-registry
(registry) precedents to **relay-as-context** (§6.2). Out of scope for v1, so
it is not silently dropped: node-spawn API, radio-send UI, live-edit UI,
signal API, consent-grant queries (§4 mechanics remain open, §8), and any
wire-visible decision-log kind — the decision log stays a section of this
manifest.

**The read surface spans all nine published kinds**, current status included:
42010 lifecycle, 42020 accounting, 42030 digests, 42040/42041 approvals,
42050 template versions, 38150 template pointer, 42060 compaction, and
**38110 node state pointer**. 38110 is not optional garnish — it is the
addressable kind that resolves "current state of node X" in one query, and a
surface that omits it reconstructs live status by replaying entire 42010
chains, which is the cost the addressable range exists to avoid.

**The generated surface derives from the signed log, not from SQLite.** The
two source paths are not interchangeable for anything published: 42020 is
run-grained *by schema* and 42030 *is* the upward aggregate, so the wire
format enforces §6.1 on its own, whereas Fractal's SQLite carries the
step-level detail those kinds deliberately exclude. Queries against SQLite
therefore stay local and unpublished; any surface that is committed, exported,
or cross-posted is built from log-derived fields only. This is what makes a
committed context surface safe to publish — it can carry no more than the
events already do.

### 5.2 Session continuity (compaction)

Evergreen sessions compact, and a compaction is a derived view that must keep
a pointer to its source. Each compaction publishes a **kind 42060** event
carrying task coordinates in tags (`branch`, `run`, `iter`, `step`, the
session id, and the compacted span) plus an `e` tag with a `summary-of` marker
resolving to the step's own lifecycle event. Content carries metrics and a
**summary hash — never summary text**, and the pointer resolves to the node's
own step event, so a child's compaction stays in its subgraph and only
digests roll up (§6.1).

**Detection reads the harness's own marker, which already exists.** Transcripts
carry an append-only `system` record with a `compactMetadata` object —
`trigger`, `preTokens`, `postTokens`, `durationMs`, `cumulativeDroppedTokens`,
and preserved-segment identifiers. Nothing upstream needs to change and
nothing needs inferring: `preTokens`/`postTokens` *are* the compaction metrics
42060 reports.

A secondary signal corroborates it where the marker is absent (older
transcripts, or a harness that stops emitting it): total prompt size
(`input_tokens` + `cache_read_input_tokens` + `cache_creation_input_tokens`)
grows across a session and drops sharply at a compaction. The third term is
required — the two-term form tracks cache turnover, not context, and fires
several false positives per session as the prompt cache expires and refills.

Every 42060 event therefore carries a `detection` tag recording which signal
produced it — `harness-marker` (primary, attested) or `usage-discontinuity`
(fallback, inferred) — so a reader can grade the claim rather than trust it
(§6.5).

**Harvester boundary.** The bridge's transcript adapter may read append-only
structured *metadata* records, `compactMetadata` among them, in addition to
per-request usage fields. It still may not parse conversational structure, and
in particular must never read the compact summary body: the harness writes the
summary text into the transcript, and 42060 carries only its hash. This
extends the adapter's original usage-fields-only boundary; the prohibition
that matters — no conversational content — is unchanged.

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
- **Decomposition economics rest on a ratio, not on specific tiers.** The
  doctrine holds because execution is cheaper than review and orchestration,
  and any tier assignment preserving that ordering preserves the doctrine
  (§3). What a retiering does change is absolute burn per child, so
  cap-sizing guidance — how large a leaf's cap must be to cover its solve plus
  wind-down — has to be restated against burn observed at the tiers actually
  in use. The existing guidance was calibrated on the cheapest tier and is
  stale; replacement figures wait on observation rather than estimation.
- **First ply:** `core` (event kinds, relay client, config — merges first),
  `bridge`, `registry`, `evergreen`, `evals` (spawned late; depends on bridge
  events).
- Full autonomous self-management is explicitly out of scope; named as
  endgame only.

## 8. Open questions

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
  2026-07-23.) **This question gates live dogfooding.** No relay endpoint is
  recorded anywhere in the repo: every publish path takes it as an
  operator-supplied `--relay` argument, and `CoreConfig.relay_url` has no
  default. A node therefore cannot discover or reach the relay on its own, so
  no node's completion may be gated on live relay data until this closes —
  demonstrations gate on the mock-relay fixture set, with the live run as an
  operator-run follow-up.
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
| 2026-07-23 | Model-policy retiering: REVIEW steps and the architect run the stronger tier, dev nodes and their children the cheaper one, orchestrator strong. Applied tree-wide by direct human directive; `tree/templates/dev-node` bumped to v2 and registered as a signed 42050 (version event `0f8d0910`, pin `c6696b7`) — the registry's first real version bump. | root (directive A6BE089F) | **Approve** — a key-component change (template + tree-wide policy) but not a structural one: it tunes an economic parameter and touches none of the four review-bar principles. Three manifest corrections applied. (1) §3 named the tiers literally ("haiku-develop/fable-review model policy"), so the manifest body had gone stale against the live tree; rewritten to state the **shape invariant** — orchestrator writes precise work orders, cheaper tier executes, stronger tier reviews — with the current assignment recorded as a tunable parameter, so the next retiering is a parameter edit and not a manifest contradiction. Surfaces that display the policy must read the live assignment, not restate it. (2) §3 described registry-backed template versions as future; they are live, and §3 now says so. (3) §7 economics: the decomposition doctrine rests on a *ratio* (execution cheaper than review and orchestration) which the new tiers preserve, so the doctrine stands unchanged; what shifts is absolute per-child burn, which makes the haiku-era cap-sizing guidance stale — flagged as awaiting observation rather than replaced with invented numbers. Corroboration: the requirements inventory independently recorded the old tier table as a live requirement, which is the argument for generating that display rather than restating it. |
| 2026-07-23 | Compaction-to-task mapping (§8) **closed** and moved into §5.2 as current truth: compactions publish a kind **42060** event carrying task coordinates in tags and an `e`/`summary-of` pointer to the step's own lifecycle event, with metrics and a summary hash — never summary text — in content. Kind allocated per a stated decade-per-family convention now recorded in §1. | root (directive 7803C28A); research `main.platform_architect.compaction` | **Adopt-with-substitution.** The child's Candidate A shape is adopted (signed, discoverable, privacy-tight, harvestable inside the one adapter per bridge condition 3). Its recommended next-step 3 — "coordinate with Claude Code's harness to emit a `compaction` transcript record" — is **rejected as unnecessary**: architect verification against the tree's own 36 transcripts found the harness **already emits** an append-only `system` record carrying `compactMetadata` (`trigger`, `preTokens`, `postTokens`, `durationMs`, `cumulativeDroppedTokens`, preserved-segment ids), so the study's central premise — "no compaction record exists today" — is false, and the upstream dependency it implied never needed incurring. Detection therefore reads the marker. A usage-discontinuity fallback is retained for transcripts lacking it, but **only** in three-term form (`input_tokens` + `cache_read_input_tokens` + `cache_creation_input_tokens`): the two-term form tracks cache turnover rather than context and produced 4–6 false positives per session in measurement, while the three-term form matched the markers 1:1 (2 drops, 2 markers, same two sessions). Each event carries a `detection` tag (`harness-marker` \| `usage-discontinuity`) so readers can grade the claim (§6.5). Bridge condition 3 is **extended**: the adapter may read append-only structured metadata records, but still may not parse conversational structure, and must never read the compact summary body — the harness writes summary text to the transcript and 42060 carries only its hash (§6.1). Condition on `core`: re-run the block/buzz collision check before writing `docs/kinds/42060-*.md` (nearest Buzz neighbour was 42000 @ 06e3d82; expected clear, but the check is core's to run). |
| 2026-07-23 | Evergreen v1 defined (§5.1): **v1 is the read plane; Fractal's CLI remains the write plane** — a query surface over the signed log plus a generator/maintainer of the standing context surface, with no write path. A v1 line is drawn through all four §5 capabilities, and v1 holds no local index, extending relay-as-cursor and relay-as-registry to relay-as-context. | root (directive 7803C28A); research `main.platform_architect.evergreen_inv` | Adopted. Of the 28 requirements the inventory derived from the handrolled prototype, 16 are relay-derivable with no query surface at all — that is where v1 belongs. Every write-side gap the inventory named (radio-send UI, signal API, live-edit UI, node-spawn bridge) is a wrapper around a working Fractal capability: wrapping adds a second control path with no new capability, and an orchestration layer over the spawn API drifts at §6.3. "Signal routing is Fractal CLI only" is the boundary holding, not a gap. §6.2 falls out clean because v1 reconstructs on demand rather than indexing. Out-of-scope items recorded in §5.1 so they are not silently dropped; a wire-visible decision-log kind is declined for v1 as governance-shaped work adjacent to the evals fence. |
| 2026-07-23 | Buzz human surface v1 (§1): cross-post set fixed — 42010/42020 → `KIND_STREAM_MESSAGE` (9) in the subgraph channel, 42040/42041 → an approvals-inbox NIP-29 group, 42030 → parent channel; 38150 and 42050 not surfaced. Two new invariants recorded: the **audience invariant** and **forward-only** (no backfill). | root (directive 7803C28A); research `main.platform_architect.buzz_surface` | **Approve-with-corrections.** The recommended 42050 → `KIND_AGENT_PROFILE` (10100) mapping is **rejected** on two independent grounds: a template is the improvable asset (§3), not a node identity (§2), so publishing versions as agent profiles conflates them; and 10100 is user-owned and globally-scoped "like kind:0" — i.e. replaceable — so each new version would clobber its predecessor and destroy exactly the diffable version history §3 exists to guarantee. If templates ever surface in Buzz it is as a stream message in a registry channel, and replaceability is to be verified first. Correction 1: the proposed tag shape embedded a JSON object as a tag element; NIP-01 tag elements are strings, so the source reference is flattened (`e`/`lindenmayer-source` plus `source_kind` and `source_created_at`), which also makes the dedup-by-reference rule (escalation D35D86E8) concrete on the wire. Correction 2 (new invariant): **a cross-post may never widen the audience of its source event** — channel membership is the only access gate, so 42030 is the sole kind eligible for a parent channel because it *is* the upward aggregate; this answers the research's open question on marking aggregate privacy scope structurally rather than with a new tag. Backfill declined: Buzz is forward-only, closing the research's open question on historical cross-posting. |
| 2026-07-24 | Commissioning review of the `evergreen` node contract (`tree/evergreen/NODE.md`, pinned 2e73599) — the first instantiation of dev-node template **v2** (@ `c6696b7`) and the first ply-node review of a *product surface* rather than a library. Reviewed for §5.1 charter fidelity, §6.1 wire-format privacy, §6.2 no-local-index, §6.5 verification, buildability under sonnet, and the two deviations the root volunteered for overrule. | root (request B92E616C) | **Approve-with-conditions** (verdict 06832636). Contract fidelity verified: the read-plane ruling is stated as the scope-defining rule with the §6.3 rationale intact, the three deliverables match the skeleton, relay-as-context with no local index is carried, the out-of-v1 list is complete (write paths, decision-log kind, consent-grant queries, eval-shaped anything), and the 42060 ownership split (bridge emits, evergreen consumes read-side) is explicit. **Deviation (a) — scope `src,tests`, not `src`+`docs/` — UPHELD, overruling the architect's own skeleton:** scopes are directory-granular, so granting `docs` would give a node under architect review commit rights over `DESIGN.md`, the manifest that defines its review bar — a governance inversion §6.4 presumes cannot happen. Residual gap closed rather than waved past: `--help` text and module docstrings live in `src` and are the node's to write; any user-facing doc *page* is architect-written from the node's escalation. **Deviation (b) — the dogfooding fixture — root asked whether it is a §6.1 leak; it is not, but it has a buildability defect root did not raise.** On privacy: safe, structurally — 42020 is run-grained *by schema* ("no per-step fields exist anywhere in this event schema"), 42030 *is* the upward aggregate, and §7 already opts this tree into full transcript publication, so the fixture discloses strictly less than `transcripts/` does. On buildability: the requirement as written is **not satisfiable by the node alone**, and is re-gated (condition 3). Three conditions. (1) **Add kind 38110** to deliverable 1 — the contract enumerates seven kinds and omits the Node State Pointer, the addressable kind that resolves current status in one query; without it the generator replays whole 42010 chains for status the 381xx range exists to make O(1). (2) **The generated surface derives from the signed-log query surface (deliverable 1), never from Fractal's SQLite directly** — the privacy answer above is load-bearing on that derivation, since SQLite carries the step-level detail the wire format deliberately excludes; committed/exported/cross-posted surfaces are log-derived only. (3) **Re-gate the live-demonstration requirement on the mock-relay fixture set** (`tests/relay_mock.py`, already in-tree), with the live run a non-blocking operator-run follow-up: no relay endpoint is recorded anywhere in the repo — every publish path takes an operator-supplied `--relay` (bridge CLI `tree/bridge/NODE.md:61`; registry hotfix `adfeab3` passing `--relay` into `CoreConfig`), `CoreConfig.relay_url` has no default (`core/config.py:67`), no deployment TOML exists, and no relay is running — so a completion gate on "live relay data" strands a finished node `exited`, the same hazard conditioned on in the `core` commissioning review (request 8AFB1E8C), condition 3. §8 amended to record that the open relay question gates live dogfooding tree-wide. **Root's CLI-argument-path-under-test hardening is CONFIRMED as the right generalization but belongs in dev-node v3, not this contract:** the failure recurred across two *independent* nodes (bridge, registry — both shipped CLIs whose argument path no test executed, both broke on first live use), which makes it a template gap; leaving it per-contract means node four re-learns it by breaking. It stays in evergreen's contract meanwhile, since v3 does not exist yet. Caps ($25/10 iters, sonnet, depth 1/children 3) judged sane and deliberately un-second-guessed: this is the run that produces the observed-burn figures the §7 recalibration is waiting on. Contract-text edits are proposals to the root (`tree/` is the root's to edit). |
