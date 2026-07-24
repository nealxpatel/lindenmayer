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
agent trees (plasma-ai/fractal) through **Nostr** — a signed, portable event
log any compliant relay can carry and any compliant client can read — turning
agent work into a versioned, evaluated, human-owned workforce. Fractal and Buzz
are external platforms this repo integrates; their code does not live here.
Lindenmayer adds no capabilities to Fractal nodes — it makes existing Fractal
primitives durable, identified, and observable on the signed log.

**Buzz is a consumer, not the thesis.** Block's Buzz (block/buzz), the
Nostr-based workspace, is the reference human surface and the project's
standing proof that the log is genuinely portable — real human value drawn out
of a general-purpose Nostr client this project does not control. It is one
consumer among possible others, never the record. This wording **corrects a
lag rather than reversing a decision**: §1 has designated Nostr, not Buzz, the
primary integration target since the Nostr-first layering, and this section had
not caught up. Nothing built depends on the correction — every component
targets the minimum relay contract, which is precisely what the layering
bought.

**Vocabulary.** "Fractal" had come to mean three things in this project's own
conversation, which is one too many for a document that governs by wording:

- **Fractal** — the agent-tree platform (plasma-ai/fractal) this repo
  integrates with. Always capitalized, always the platform.
- **tree** / **subgraph** — a running instance: a graph of nodes rooted at a
  branch. What you steer, what exits, what costs money.
- **capability** — the durable asset: a template plus a persistent role
  identity plus that identity's version-scoped track record (§2). This is the
  thing an organization owns and a person is granted authority over — e.g.
  `looker-data-model`. It outlives any particular tree.

"Fractal" is retired from the third sense. The distinction is not pedantry:
§1's revocation rule, §2's identity scoping, and §4's grants are all
statements about *capabilities*, and they read as nonsense if applied to a
run.

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
    approval, 42050 template, 42060 compaction, 42070 commission, 42080/1
    grant and grant-revocation — with the units digit
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
  to a **durable owner key** — an organization or seat key, not an individual
  person (an `auth` tag — owner pubkey, conditions, BIP340 signature —
  attachable to any event; restated in `docs/kinds/nip-oa-attestation.md`).
  The attestation chain is core (verifiable anywhere); relay-enforced instant
  revocation is Buzz-layer (see §2). **A human's authority over a subgraph is
  a grant, not an attestation** (§4): revoking a person revokes their grants
  and leaves the subgraph, its identity, and its track record intact. NIP-OA
  needs no extension to carry this — its owner field is a pubkey, and the
  draft nowhere requires that pubkey be a person.
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
signs. A persistent node maps one-to-one onto a Buzz agent at the **role**
level — not a tree, not a run; ephemeral workers map to nothing, which is
correct rather than lossy, since a subgraph's internals are not representable
in a flat agent model and §6.1 says they should not be visible there anyway.

**Identity is role-scoped; trust is version-scoped.** These are separate axes
and the interaction is the whole point:

- **One npub per role, persisting across runs and across template
  revisions.** Minting a new identity per version would fragment the track
  record exactly where continuity is the asset, and would churn the agent
  roster on every template edit.
- **Revision keeps the identity; forking mints a new one.** A template
  revision (dev-node v2 → v3) leaves the role and its npub untouched. A
  *fork* — deriving `looker-data-model` v1 from dev-node v3 — is a new role
  with a new identity. The 42050 inherit `e`-tag records **design ancestry,
  not reputation transfer**: a forked template arrives with a documented
  lineage and an empty track record, never pre-trusted on an unrelated role's
  history.
- **Trust is scoped to the version in force.** The honest claim is "this
  role, under v3, has N clean runs" — so a version bump re-enters probation
  while the longer identity history persists and stays readable. A role's
  reputation is therefore a series, not a scalar.

Together these define the platform's durable asset: a **capability** is a
template plus a role identity plus that identity's version-scoped track record
(vocabulary, §0).

**Key roles are separate and must not be conflated.** Three distinct keys are
in play, and two of them are routinely called "owner":

- **Author key** — a human's own key. Signs **template versions**, because a
  template is authored work product (§3).
- **Durable owner key** — the org or seat key of §1. What a **node's**
  keypair is attested *to* via NIP-OA's `auth` tag, whose spec field is
  confusingly also named `owner`.
- **Node key** — the node's own keypair, which signs the node's own events.

So the registry's existing 42050 events, signed with a human's key, are
correct as issued: a human wrote those templates, and authorship is not
attestation. Where this document says "owner key" unqualified it means the
durable key of §1; template authorship is always "author".

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

**Adoption is explicit, never automatic on publish.** Publishing v3 does not
upgrade anything: a live role adopts a version by a recorded event, and until
it does it runs the version it adopted. Silent upgrade-on-publish would
destroy version→outcome attribution, which is the claim the analytics rest on
— you cannot say "v3 has N clean runs" if instances migrate underneath the
measurement. Fractal agrees structurally: a node's seed is immutable for the
duration of a run, so an adoption can only ever take effect at a run boundary.

An agent's Buzz-layer profile (kind 10100) may advertise the version behind
it, so a human deciding whether to trust an agent can see it. Two constraints,
both drawn from failures already recorded here. The profile carries
**resolvable coordinates** — an `a` tag to the 38150 template pointer plus the
adopted 42050 event id — never a transcribed version string: a restated
version goes stale silently, exactly as the restated tier table did. And the
profile is a **derived pointer, never the record**: 10100 is replaceable, so
it holds current truth only, and where it disagrees with the adoption chain
the adoption chain wins.

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

**Grants: one primitive, three uses.** Consent and authority share a single
mechanism — a **signed, revocable, expiring grant event** (kind 42080; its
revocation is a separate append-only 42081, because a replaceable grant would
clobber the evidence that authority once existed). Whatever a grant conveys,
the same facts land in the log: who granted what to whom, for which purpose,
over which window, and whether it was revoked — never rows in a side policy
store.

The three uses:

1. **History access for training.** A human grants time-limited access to
   their history, to a node or to another human. Grants exist to facilitate
   fine-tuning for a given task or project; the training itself runs on
   hosted inference/tuning infra and is future development.
2. **Management authority.** A human's evergreen node (§5) holds a revocable
   grant of authority over named subgraphs. This is what makes §1's durable
   attestation work: the org holds the capability, a person currently holds
   authority over it, and revocation targets the grant.
3. **Succession.** A departing human's grants are revoked and equivalents
   issued to their successor's evergreen node, optionally with read access to
   prior history so the successor can learn what happened.

**Why one kind and not three.** Not because the three share a shape — reuse is
evidence of economy, not of correctness. They share **revocation semantics**,
which is the property that actually has to match: the revoker is the grantor
in every case (the grantor's identity varies because the resource varies,
which is a field and not a difference in meaning); the blast radius is
forward-only in every case (revoking history access stops future extraction
while already-extracted rows stand, labeled with their attestation state at
extraction time; revoking management authority stops future commissioning
while a running node's immutable seed carries its run to completion); and
expiry is identical. A `scope` tag distinguishes them. Had the revoker
differed — had one grant been revocable by someone other than whoever issued
it — they would be distinct kinds regardless of how alike they looked.

**What grants do not yet do.** Nothing enforces a management grant today:
Fractal does not read the signed log, so a grant is a governance fact of the
same standing as a decision-log row — real, verifiable, and not a gate.
Commissioning (§5.3) is what first gives grants a consumer that checks them.

Extraction pipelines honor grants and their expiry/revocation, respecting
§6.1 (mechanics open, §8).

**Succession costs nothing at the attestation layer, and that is the argument
for §1's durable owner key.** NIP-OA has no revocation primitive at all — its
conditions grammar admits only `kind=` and `created_at` bounds, and the draft
states plainly that attestations are never revoked, only superseded by a newer
attestation. Under a person-attested model, every departure would require
reissuing every attestation in the subgraph, and the spec gives no clean way
to do it. Under §1's durable key the attestation never changes on succession
at all: only grants move. NIP-OA's weakest property stops mattering.

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

**A custom human-facing UI is evergreen v2, not a separate node.** The shape is
one generator with several rendering targets — signed log → query surface →
{markdown context surface, UI, optionally NIP-AO frames}. Ownership follows
commit rights over the query surface rather than the look of any target: a
separate node would need write access to the surface evergreen already owns.
The read/write split above binds every target, so the UI is read-only; NIP-AO
ranks second and optional, and is `bridge`'s (frames are ephemeral by spec, so
§6.2 bars them from carrying record).

The write-side gaps are real but they are not ours to fill. Radio send,
signals, live `NODE.md` edits, and node spawn are Fractal capabilities that
already exist and work; wrapping them would add a second control path with no
new capability, and an orchestration layer over Fractal's spawn API drifts
straight at §6.3. That signal routing is "Fractal CLI only" is not a gap —
it is the boundary holding. The read side is the opposite case: most of what
the prototype needs is reconstructable from the signed log, and none of it has
a query surface today.

**The read/write split governs the Fractal control plane, not the log.**
Evergreen publishing a signed event is not a write-plane breach — publishing
to the log is what every component in this platform does, and bridge and
registry already do it. What evergreen may not do is *drive Fractal*. The
distinction matters because the two get conflated: "no write path" has been
read as "evergreen never signs anything," which would bar it from the one
thing §5.3 shows is both safe and necessary. The governing test is §6.5's
competing-assertion rule, not the medium.

**Approvals are not an exception to the read plane.** They are the most
tempting place to breach it — a human approving from the surface they are
already reading is obviously valuable, and signing a 42041 verdict looks like
using a native Nostr primitive rather than wrapping Fractal's CLI. The
objection is real but it is not what decides the question. What decides it is
what happens *after* the signature. Either something translates the signed
verdict back into the Fractal radio reply that actually releases the gate — a
second, automated control path over Fractal's own contract, which is exactly
what §6.3 and the read-plane rule forbid — or nothing does, and the platform
now holds two records of whether work was approved, which can disagree (§6.2).
Both outcomes are worse than the status quo, in which Fractal's gate and the
signed record cannot diverge because only one of them is authoritative.

The condition that would reverse this is specific: **if Fractal itself gains a
native input that reads approvals from a signed log**, the control path becomes
Fractal's own contract rather than our wrapper, and the objection dissolves.
That is an upstream capability, not one this project may add (§6.3). Until
then, human-facing approval *actions* stay Fractal-CLI-only and every human
surface — including any future UI — is **read-only** with respect to them. The
approvals *queue* (42040 pending, 42041 verdicts) remains fully in scope to
display; it is the acting, not the seeing, that is withheld.

| §5 capability | v1 ships (read) | Stays Fractal CLI (write) |
|---|---|---|
| Commission trees | template catalog: versions, history, instance linkage | the spawn itself |
| Steer subgraphs | situational awareness: aggregates, budgets, pending gates | radio send, signals, live edits |
| Review approvals | the queue: 42040 pending, 42041 verdicts | the verdict (a radio reply) |
| Query own history | owned fully — this *is* the capability | — |

The "commission trees" row is the one that moves at v2: the commission itself
(§5.3) is evergreen's, the spawn stays Fractal's permanently. The v1/v2 line
runs *through* that capability, not around it.

The generated context surface is a composite: a human-authored preamble
(mission, phase, non-negotiables, governance mode, pointers) plus a generated
situational block derived from queries. That is what the handrolled prototype
already is, minus the hand maintenance.

v1 holds no local index — it reconstructs from the relay and Fractal's SQLite
on demand, extending the relay-as-cursor (bridge) and relay-as-registry
(registry) precedents to **relay-as-context** (§6.2). Out of scope for v1, so
it is not silently dropped: node-spawn API, radio-send UI, live-edit UI,
signal API, and any wire-visible decision-log kind — the decision log stays a
section of this manifest. The commission path (§5.3) and grant queries (§4)
are **v2**, not v1: v1's kind set is closed at the nine below, and 42070 /
42080 / 42081 are allocated but unbuilt.

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

### 5.3 Commissioning, intake, and the requester front door

Everything in this subsection is **evergreen v2**. v1 (§5.1) remains the read
plane with no write path of any kind, and its kind set stays closed at nine;
nothing here loosens that. What follows is the design v2 builds to, decided
now because the v1 contract is being written against it.

**Commissioning is a composite capability, and most of it is not Fractal's.**
What an operator actually does to commission a node is not `fractal node
init`. It is: resolve the current template version from the registry; generate
the contract and commit it for a pin; price the caps; author the runtime seed
citing that pin; pin the review model; route to the architect for countersign;
apply the returned conditions; write the numbered work order. That composite
spans registry, governance, and Fractal, and Fractal cannot perform it. Left
manual it has three costs: the instance→template-version linkage is a line
someone types rather than a fact created by construction; commissioning leaves
no trace in the signed log, which is why the analytics have a hole exactly
where the operator stands; and if the normal usage pattern requires dropping
to the Fractal CLI, the control surface is a dashboard.

**The composite is in scope; the spawn is not.** The seam is exact:

- **In scope — the commission.** Everything up to and including the work
  order, published as a **kind 42070 commission** event: a signed, complete,
  executable specification naming the template version and pin, the priced
  caps, the countersigning architect and its conditions, and the authorizing
  grant (§4).
- **Out of scope — the spawn.** `fractal node init` stays the operator's, run
  through Fractal's own CLI. Wrapping it would be the orchestration layer
  §6.3 bars, and the §5.1 table already says so.
- **The linkage, obtained without touching the spawn.** The instance's 42010
  lifecycle event carries a `commission` reference. Bridge already emits
  42010, so instance→commission→template-version becomes a fact created by
  construction — which is what the manual line was failing to guarantee.

**Which record is authoritative — the question that killed approvals — does
not arise here.** Fractal's registry records what *runs*; the commission
records what was *authorized*. Those are different propositions, so they
cannot contradict each other, and where they differ the difference is a
finding with a reader — an instance running outside its commission is
precisely the governance signal this platform exists to surface — rather than
a silent divergence with no one to adjudicate it. Stated generally, this is
§6.5's competing-assertion rule, and it is also why the approvals deferral is
unaffected: **authorization-without-execution is a coherent state;
approval-without-release is not.** A commission never spawned is an
authorization not yet used, which reads true. A verdict that never released
the gate is a record claiming work was approved while the work sits blocked.

**Intake belongs to evergreen, not to a second node.** Evergreen receives
external work requests, verifies them against downstream template
preconditions, converses with the requester about missing requirements, and
produces a validated commission. It was tempting to separate this — one node
holding the owner's full context while talking to outsiders looks like a §6.1
hazard — but the separation is worse on its own terms. The boundary would be
illusory: a node that validates requirements against template preconditions
*and* prices them needs capability, budget, and priority context, which is
owner context, so separation yields two partially-informed nodes and a
synchronization problem rather than isolation. And the structural gate already
exists at the right layer — channel membership (§1) — so node separation would
be a second mechanism for what the channel already does. Two persistent
identities per human is also the exact fragmentation evergreen exists to end.

The discipline is **read broadly, write narrowly**, and it is structural
rather than behavioral: evergreen queries its own subgraph privately, and
**every outbound surface to non-owners is built from log-derived fields
only** — the same rule §5.1 already binds the generated context surface with,
for the same reason. A surface that can carry no more than the events do
cannot over-share by mistake.

**The mention front door.** A person in Buzz who wants work done has no path
today and will never open a terminal; a Buzz mention of an agent's npub
becomes a radio message to that human's evergreen node, carrying a reference
to the source event. This is an inbound cross-post, not an operator wrapper:
it duplicates no existing path, and the two records assert different things —
the Buzz message is the origin, the radio message the effect, the link
explicit — which is the distinction from approvals, where a signed verdict and
Fractal's gate state would assert the same proposition. Four conditions bind
it:

1. **Listener, not harness.** We subscribe to channels and filter for
   mentions of our agents' npubs, then translate to radio. Buzz's ACP harness
   is not adopted; Fractal remains the sole orchestrator.
2. **Propose, not dispose.** Evergreen never spawns work from a mention. It
   produces a requirements-complete commission the human approves — which is
   also what closes the budget question, since no spend moves before that
   approval: a mention costs a read, not a run. Per-requester allowances
   bound the read.
3. **Authorization is channel membership** (§1's only access gate), not the
   ability to type an `@`.
4. **Idempotency keys on the source event id.** A commission is an upsert
   against that key, so a redelivered mention is a no-op, and an edited
   mention — a new id, since Nostr ids are content-addressed — supersedes
   rather than duplicates.

**Registration is not mentionability**, which resolves a UX lie without
narrowing §2's role-level agent mapping: any persistent role may register a
profile so its identity and track record are visible, but only evergreen
advertises an intake capability and answers. Registering silent working nodes
as mentionable agents would promise a reply that never comes.

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

   **The integrated-graph claim rests on shared identity and a shared log, not
   on a shared application.** The question has been put directly — does making
   Buzz optional weaken "humans and AI as one integrated organizational graph"?
   It does not, and the reason is structural rather than rhetorical. Every
   mechanism this principle actually relies on lives below the client:
   channel membership as the sole access gate is **NIP-29**, a relay feature;
   aggregates-up is enforced by the *kind schemas* (42020 is run-grained by
   schema, 42030 *is* the aggregate); and the one-hop parent↔child visibility
   bound is Fractal's radio topology (§5). None of the three lives in the Buzz
   desktop client, so a different client reading the same relay inherits all of
   them unchanged. The strongest counter-argument — that a bespoke dashboard
   turns agents into a fleet you monitor, whereas agent work in the inboxes
   humans already inhabit makes agents colleagues — is a claim about **ambient
   presence**, and it survives: presence is the one thing a separate
   application genuinely cannot replicate. It is a reason to keep a Buzz-layer
   presence surface, not a reason to make Buzz the record.
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

   **Corollary — a relay filter is a bandwidth optimization, never a
   correctness boundary.** Every constraint a consumer depends on is re-checked
   client-side after signature verification, including constraints the consumer
   also sent to the relay. This is principle 5 one level deeper, and NIP-01
   makes it sharper than it looks: tag filters are defined only for
   **single-letter** keys (`#e`, `#p`, `#d`, …). A multi-character key such as
   `#branch` or `#template_name` is not merely unenforced — a conformant relay
   *silently ignores it* and answers the remaining terms, returning a superset
   that looks filtered. The failure is invisible at the call site: the query
   succeeds, the events are real, they are simply the wrong ones. Two rules
   follow. Only single-letter `#<x>` keys may be sent as tag filters at all.
   And any constraint expressible only as a multi-character tag is enforced in
   the client, after `verify()`, or not claimed.

   This is also a §6.1 concern, not only a correctness one: a surface labelled
   for one branch that silently answers with every branch's events is an
   aggregates-up violation, which makes such a defect blocking rather than
   cosmetic.

   **Corollary — a new signed record is safe exactly when Fractal holds no
   competing assertion of the same proposition.** This is the general form of
   the objection that barred approvals, and it decides every write-path
   question the platform has faced without needing a fresh argument each time.
   Where Fractal already asserts the proposition, a second record can diverge
   from the one that actually governs execution, and something must reconcile
   them — a second control path, which §6.3 forbids. Where Fractal asserts
   nothing, the signed record is the only record and divergence is impossible
   because there is nothing to diverge from.

   | Path | Fractal's competing assertion | Ruling |
   |---|---|---|
   | Approval verdict → gate | gate state: approved or not | barred |
   | radio-send / signal / kill wrappers | the message, the signal, the kill | barred |
   | Commission authorization (§5.3) | none — Fractal has no concept of authorization | permitted |
   | Inbound @mention → radio (§5.3) | none — the mention originates outside Fractal | permitted |

   The test is the *proposition*, not the medium: publishing a signed event is
   never itself the violation, and wrapping a CLI is never itself decisive.
   What matters is whether two records can answer the same question
   differently.

   **Shared test doubles may never be more permissive than the strictest
   conformant real implementation.** A mock relay that honors multi-character
   tag filters would make every consumer's tests pass against behavior no real
   relay exhibits, masking this entire class tree-wide. When a faithful double
   makes a bug invisible, the defect is in the caller, never in the double —
   the double is doing its job.

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
  2026-07-23.) **This question gates live dogfooding — on reproducibility,
  not on reachability.** The earlier form of this bullet said no relay is
  reachable from inside a node run. That is **false and has been corrected**:
  an operator-run dev relay answers on `ws://localhost:7100` (measured from
  inside a node run; it is the relay the evergreen requirements inventory
  recorded as holding 12 node identities and live 42010/42020 events).

  What is actually missing is a *reproducible deployment*. There is no
  `deploy/`, no compose file, and no deployment TOML, so the endpoint exists
  only as operator ambient state and in a research document — nothing a node
  can discover. Worse, the one endpoint recorded in code disagrees with it:
  `registry`'s CLI defaults to `ws://localhost:8080` (`registry/cli.py:35`),
  a port nothing is listening on, while `bridge` requires `--relay`
  explicitly and `CoreConfig.relay_url` has no default at all. A node
  following the only default in the tree reaches nothing.

  The gating rule therefore stands, on corrected grounds: completion gates on
  the mock-relay fixture set, with live runs an operator-run follow-up — not
  because a relay cannot be reached, but because no node can *discover* the
  right one, and the recorded default is wrong. Closing this question means
  a checked-in deployment and one endpoint of record, after which live gating
  becomes legitimate.
- **Grant mechanics.** The model is decided — one signed, revocable, expiring
  grant kind (42080) with a `scope` tag covering history access, management
  authority, and succession, plus 42081 for revocation (§4). Open: the tag
  schema (Nostr has prior art in NIP-40 expiration and NIP-09
  deletion/revocation), grant granularity (whole history vs. per-channel vs.
  per-subgraph vs. per-time-range), how extraction pipelines enforce expiry
  and revocation, what revocation means for training runs already in flight,
  and integration with hosted tuning infra (Baseten/Fireworks-type).
- **What issues an org/seat key, and who holds it.** §1 attests subgraphs to a
  durable owner key rather than to a person, and §4 moves authority by grant.
  Neither says how an org key is created, custodied, rotated, or recovered —
  and a lost org key is worse than a lost personal one, because it strands
  every capability attested to it. Succession is specified at the grant layer
  and unspecified at the key layer.
- **Commission conformance.** §5.3 makes an instance running outside its
  commission a visible finding, but nothing yet *checks* it. Open: whether
  the comparison (42070 commission vs. the 42010 the instance actually
  emitted, vs. Fractal's registry row) runs in the read surface as a query, or
  whether drift is merely displayable. No enforcement is proposed — Fractal
  does not read the log — so the question is what the platform asserts about
  drift it can see, and how loudly.

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
| 2026-07-24 | NIP-01 tag-filter conformance raised to a §6.5 corollary: only single-letter `#<x>` keys may be sent as relay tag filters, because a conformant relay *silently ignores* a multi-character key (`#branch`, `#template_name`) and answers the remaining terms — returning a superset that looks filtered. Any constraint expressible only as a multi-character tag is enforced client-side after `verify()`, or not claimed. Shared test doubles may never be more permissive than the strictest conformant real implementation. | `main.evergreen` (escalation 6D3D3C19) | **Confirmed — diagnosis and client-side fix approved**, and generalized rather than patched at the two call sites. Architect re-verified independently instead of ruling on report: `tests/relay_mock.py:30` gates on `key.startswith("#") and len(key) == 2`, so the shared mock is genuinely NIP-01-faithful — which is *why* no test catches this, and why loosening it (correctly reverted by the reporter) would have masked the class tree-wide; `src/lindenmayer/registry/reader.py:72` sends `#template_name` and the loop below reads the tag into `version_name` without ever comparing it to the requested name. **Architect sweep beyond the report:** every `#`-prefixed filter key in `src/` is `#d`, `#h`, or `#template_name` — the first two single-letter and spec-valid — so the blast radius is exactly one line, making this a one-line fix plus a standing rule, not a migration. `registry` to apply the same client-side re-check shape `evergreen` used. The §6.1 reading is upheld: a branch-labelled surface answering with twelve other subgraphs' events is an aggregates-up violation, hence blocking rather than cosmetic. |
| 2026-07-24 | Founding thesis (§0) restated: Lindenmayer governs Fractal subgraphs **through Nostr** — a signed, portable event log — with Buzz the reference human surface and portability proof, one consumer among possible others, never the record. §6.1 gains the structural argument that the integrated-organizational-graph claim rests on shared identity and a shared log rather than a shared application. | root (directive 40AF5961, supplement 5A02BFF1) | **Approved as a correction, not a revision** — the substantive decision was already taken by the Nostr-first layering (directive 5CD20B25), which made Nostr the primary integration target; §0 had simply lagged its own architecture since, and this closes the gap. Nothing built is at risk precisely because every component targets the minimum relay contract. The root's request to argue the opposite case was honored and the strongest form of it identified — §1 names channel membership as the sole access gate, so a bespoke surface appears to require rebuilding the very gate §6.1 calls structurally enforced — but it **dissolves on inspection**: that gate is NIP-29, a *relay* feature, and aggregates-up is enforced by kind schema while one-hop visibility is Fractal's radio topology, so none of the three mechanisms lives in the Buzz client and any client on the same relay inherits all of them. The surviving residual is **ambient presence**, which a separate application genuinely cannot replicate — an argument for keeping a Buzz-layer presence surface, not for making Buzz the record. Root to apply the parallel edit to repo `CLAUDE.md` (root-owned). **Deliberately not ruled here:** UI ownership (evergreen v2 vs. new ply node) and NIP-AO priority, both of which hinge on a negative existence claim about Buzz's rendering surfaces that is under independent verification by `main.platform_architect.buzz_render`; ruling them on the proposing node's own unverified enumeration would repeat a known failure mode. |
| 2026-07-24 | §8 relay bullet corrected: the open relay question gates live dogfooding on **reproducibility, not reachability**. The prior claim that no relay is reachable from inside a node run is withdrawn as false. | architect self-correction, surfaced by `main.evergreen` (escalation 6D3D3C19, which measured against `ws://localhost:7100`) | **Corrected.** Verified from inside a node run during review: port 7100 answers, and `docs/research/evergreen/inventory.md` records that relay holding 12 node identities with live 42010/42020 events — so the reachability claim was false while it stood, and it had already been used to justify a tree-wide gating rule. The gating rule itself **survives on corrected grounds**: no `deploy/`, compose file, or deployment TOML exists, so the endpoint is operator ambient state a node cannot discover, and the sole default recorded in code (`registry/cli.py:35`, `ws://localhost:8080`) points at a closed port while `bridge` requires `--relay` and `CoreConfig.relay_url` has no default. A node following the only default in the tree reaches nothing. Closing the question means a checked-in deployment plus one endpoint of record. Same failure family as the two corrections already logged (a false premise accepted from a child; "registration is live" over-implying reachability) — a claim about *absence* asserted without measurement, which then hardened into a constraint on other nodes' completion gates. |
| 2026-07-24 | Approvals confirmed **not** an exception to the evergreen read plane (§5.1): human-facing approval actions stay Fractal-CLI-only, and every human surface — including any future UI — is read-only with respect to them. The approvals *queue* remains fully in scope to display. | root (directive 40AF5961, question d) | **Reject-with-reasoning**, on different grounds than the request anticipated. The request's argument — that signing a 42041 uses a native Nostr primitive rather than wrapping Fractal's CLI — is accepted as far as it goes and is not what decides the question. What decides it is what happens *after* the signature: either something translates the signed verdict into the radio reply that actually releases Fractal's gate, which is a second automated control path over Fractal's own contract (§6.3, §5.1), or nothing does and the platform holds two records of approval that can disagree (§6.2). Both are worse than a status quo in which only one record is authoritative. Recorded as a **deferral with a named trigger, not a permanent no**: if Fractal gains a native input that reads approvals from a signed log, the control path becomes Fractal's own contract and the objection dissolves — an upstream capability this project may not add itself (§6.3). |
| 2026-07-24 | UI ownership settled (§5.1): a custom human-facing UI is **evergreen v2**, not a new ply node — one generator with several rendering targets (signed log → query surface → {markdown context surface, UI, optionally NIP-AO frames}). Per the approvals ruling above, that UI is read-only. | root (directive 40AF5961, question c) | **Approve**, and — reversing the deferral recorded two rows above — ruled **without** the verification it was held for. Held pending `main.platform_architect.buzz_render` on the belief that it hinged on whether the Buzz client can render a tree; on re-reading it does not. The question is **who holds commit rights over the query surface**, and a new node would need write access to the surface `evergreen` already owns — a governance regression regardless of Buzz's capabilities, and the same directory-granular scope hazard the evergreen commissioning review (verdict 06832636, deviation (a)) upheld. A rendering target is not an ownership boundary. |
| 2026-07-24 | NIP-AO ranked **second and optional** behind the UI, and owned by `bridge` rather than `evergreen` (derived outward publishing is bridge's half); frames may never carry record. | root (directive 40AF5961, question f) | **Approve-with-substitution of grounds.** Also released without the pending verification, and for a stronger reason: NIP-AO frames are **ephemeral by spec**, so §6.2 disqualifies them as a carrier of record *before* any question of what Buzz can render arises. The layering argument the directive offered is therefore not needed — were Buzz to render graphs perfectly tomorrow, NIP-AO would still not be the record. |
| 2026-07-24 | **Negative existence claims are not load-bearing evidence** (§6.5 corollary): a design decision rests on what a component *must* do — spec, schema, governance — never on what an investigator failed to find. "No extension surface exists" is a premise, not a finding. Where such a claim is the only support for a decision, either re-ground the decision on positive constraints or record it as open. | architect standing rule; arising from `main.platform_architect.buzz_render` (exited on budget, claim unresolved) | **Adopted.** The verification spawned to test the claim "the Buzz desktop client structurally cannot render a tree" exhausted $4.03 and closed nothing — but it did move the claim's framing twice (a *second* frontend kind gate `CHANNEL_TIMELINE_CONTENT_KINDS` distinct from the backend `TIMELINE_KINDS`; a real feature-flag system, so "only compiled, never configurable" is undercut), which is the pattern: unfalsifiable premises erode without ever resolving. The operational lesson is cheaper than the rule — **check what a held question actually rests on before funding the work to answer it**: both questions above were released on grounds independent of the premise, so the second child that would have chased it was never spawned. Same failure family as the three corrections already logged, all of them claims about *absence* asserted without measurement. Aggregate and the six open axes in `docs/research/buzz-render/`, recorded as OPEN. |
| 2026-07-24 | **The competing-assertion rule** (§6.5 corollary): a new signed record is safe exactly when Fractal holds no competing assertion of the same proposition. Where Fractal already asserts it, a second record can diverge from the one that governs execution and something must reconcile them (§6.3); where Fractal asserts nothing, the signed record is the only record. The test is the *proposition*, not the medium. | root (directives 35718844, 2A25343E); architect generalization | **Adopted**, and it is the general form of the objection that barred approvals — extracted because the same argument was about to be re-litigated case by case. It settles four questions at once and, importantly, does not settle them all the same way: approvals and the radio/signal/kill wrappers stay **barred** (Fractal asserts gate state, the message, the signal, the kill); commission authorization and inbound @mention are **permitted** (Fractal asserts nothing about authorization, and nothing about an event that originated outside it). Two corollaries the prior wording obscured: publishing a signed event is never itself the violation, and "it wraps a CLI" is never itself decisive. |
| 2026-07-24 | Identity × version policy (§2): identity is **role-scoped**, one npub per role persisting across runs and template revisions; version **adoption is explicit and event-recorded**, never automatic on publish; **revision keeps the identity, forking mints a new one**, with 42050's inherit `e`-tag recording design ancestry and never reputation; **trust is version-scoped** while identity is role-scoped. Key-role separation confirmed: templates signed by their human author, nodes by their own keypairs attested per NIP-OA. | root (directive 35718844, item 1) | **Approve (a)–(d) as proposed; (e) approve-with-condition.** The four core clauses are mutually reinforcing and were ruled together with the revocation defect below, because one decides *when* a new identity is minted and the other decides *what* identity hangs off — approving them in separate passes risks a role-scoped identity that does not compose with an org-scoped attestation. On (e), a kind-10100 profile advertising the current version is approved only as a **derived pointer**: it carries resolvable coordinates (`a` tag to the 38150 pointer plus the adopted 42050 id), never a transcribed version string, because a restated version goes stale silently — the identical failure §3 already records against the restated tier table — and 10100 is replaceable, so where it disagrees with the adoption chain the chain wins. The root's assumption about tonight's three 42050 events is **confirmed correct**: a template version is human-authored work product, so the owner key is the right signer. §2 gains the definition these clauses jointly produce — a **capability** is template + role identity + version-scoped track record. |
| 2026-07-24 | §1 revocation **defect** corrected: subgraphs are attested to a **durable org or seat key**, not to an individual. A human's evergreen node holds a revocable grant of management authority; succession revokes the departing human's grants and issues equivalents to the successor, optionally with read access to prior history; the evergreen node itself — preferences, standing context, filters — is non-transferable. | root (supplement 2A25343E, item 1) | **Accepted as a defect, not a preference**, and clauses (a)–(d) approved as proposed. The prior wording ("revoking the human revokes the subgraph") is coherent for a personal tree and destroys org capital on every departure: a capability's template lineage, track record, and eval history belong to the organization, not to whoever currently runs it. **The strongest argument for (a) is one the request did not make:** NIP-OA has *no revocation primitive at all* — its conditions grammar admits only `kind=` and `created_at` bounds, and the draft states attestations are never revoked, only superseded. Person-attestation would therefore require reissuing every attestation in a subgraph on every departure, with no clean mechanism to do it; under a durable owner key the attestation never changes on succession and only grants move, so NIP-OA's weakest property stops mattering. On (f), the request's premise is **half wrong and was verified rather than accepted**: NIP-OA's owner field is a *pubkey* and the draft nowhere requires it name a person, so an org key substitutes with **no new kind and no spec change**. What genuinely needs its own kind is the *grant* — which is the §4 primitive already owed, core-layer and ours, not a NIP-OA replacement. |
| 2026-07-24 | Grants unified (§4): **one kind, three uses** — history access for training, management authority over subgraphs, and succession — as kind **42080** with a `scope` tag, revoked by append-only **42081**. §8's history-grant question generalized to grant mechanics; two new open questions recorded (org/seat key custody; commission conformance). | root (supplement 2A25343E, item 1(e)) | **Approve, with the offered ground rejected and replaced.** The request argued that one primitive serving three jobs is evidence the abstraction is right; it is not — reuse is evidence of economy, and a shared *shape* proves nothing. The test applied instead is shared **revocation semantics**, which the three uses pass: the revoker is the grantor in every case (the grantor's identity varies because the resource varies — a field, not a difference in meaning); the blast radius is forward-only in every case (revoked history access stops future extraction while already-extracted rows stand labeled per §4; revoked management authority stops future commissioning while a running node's immutable seed carries its run out); expiry is identical. Had the revoker differed — one grant revocable by someone other than its issuer — they would be distinct kinds however alike they looked. Revocation is a **separate append-only event** rather than a replaceable update, because a replaced grant would clobber the evidence that authority once existed. Recorded honestly: nothing enforces a management grant today, since Fractal does not read the log, so a grant is a governance fact of decision-log standing until commissioning gives it a consumer. |
| 2026-07-24 | Commissioning (new §5.3): **commission-from-registered-template is in scope; the spawn is not.** Everything through the numbered work order — registry version resolution, contract generation and pin, priced caps, seed authorship, architect countersign, applied conditions — publishes as a **kind 42070 commission** event; `fractal node init` stays operator-run via Fractal's CLI. The instance's 42010 carries a `commission` reference, making instance→template-version a fact created by construction. §5.1's read/write split is reframed: it governs the **Fractal control plane, not the log**. | root (directive 35718844, item 2) | **Approve-with-conditions**, reopening the read-plane ruling on the narrow grounds requested. The composition-vs-wrapping argument is **accepted**: most of the commissioning composite is not a Fractal capability, Fractal cannot perform it, and leaving it manual costs three specific things — a hand-typed version linkage, an analytics hole exactly where the operator stands, and a control surface that is really a dashboard. But the composite still *contains* the spawn, so it is split at that seam rather than approved whole. On the authority tension the root flagged and declined to assume away: the registry records what **runs**, the commission records what was **authorized** — different propositions, so they cannot contradict, and where they differ the difference is a *finding with a reader* (an instance running outside its commission) rather than a silent divergence, which is precisely what approvals lacked. The approvals deferral is therefore **unchanged and better grounded**: authorization-without-execution is a coherent state, approval-without-release is a record that lies. Conditions: 42070 names the authorizing grant (§4); v1's kind set stays closed at nine, with 42070/42080/42081 allocated but unbuilt; `core` re-runs the block/buzz collision check before writing the registry entries. |
| 2026-07-24 | Evergreen **absorbs intake** (§5.3): one persistent identity per human. Evergreen receives external requests, validates them against template preconditions, converses with requesters, and produces a commission the human approves. | root (supplement 2A25343E, item 2) | **Approve the merge**, reversing the architect's earlier §6.1 objection. The root asked for the strongest form of the separation case — that a structural boundary beats a behavioral discipline — and it is made and then defeated on two counts. The boundary is **illusory**: a node that validates requirements against template preconditions *and* prices them needs capability, budget, and priority context, i.e. owner context, so separation yields two partially-informed nodes plus a synchronization problem rather than isolation. And the structural gate **already exists at the right layer** — channel membership (§1) — so node separation would be a second mechanism for what the channel does. Condition, which converts the root's "read broadly, write narrowly" from a behavior into structure: evergreen's outbound surface to non-owners is built from **log-derived fields only**, the identical rule §5.1 already binds the generated context surface with. A surface that can carry no more than the events do cannot over-share by mistake. |
| 2026-07-24 | Inbound **@mention front door** (§5.3): a Buzz mention of an agent npub becomes a radio message to that human's evergreen node, carrying a reference to the source event. Four binding conditions: listener-not-harness; propose-not-dispose; authorization by channel membership; idempotency keyed on the source event id. Registration ≠ mentionability. | root (supplement 2A25343E, item 3) | **Veto lifted — approve-with-conditions.** The crux the request named is (b), and it **holds**: the mention and the radio message assert different things — origin and effect, with the link explicit — where a signed approval verdict and Fractal's gate state would assert the same proposition. Confirmed by the competing-assertion rule logged above rather than by analogy. (a) is also accepted on its own terms: this creates the only path that exists for requesters who will never open a terminal, which is new capability, not a duplicate operator path. The (f) items are **specified rather than deferred**, and one dissolves — the root listed budget as a hole, but their own propose-not-dispose clause closes it, since no spend moves before the human approves a commission, so a mention costs a read and not a run; per-requester allowances bound the read. Idempotency keys on the source event id as an upsert, so redelivery is a no-op and an edited mention (new content-addressed id) supersedes rather than double-commissions. **Registration is separated from mentionability**, which resolves the UX lie the root flagged without narrowing the role-level agent mapping: any persistent role may register a profile, but only evergreen advertises intake and answers. |
| 2026-07-24 | Vocabulary fixed (§0): **Fractal** = the platform; **tree/subgraph** = a running instance; **capability** = the durable asset (template + role identity + version-scoped track record). "Fractal" retired from the third sense. Persistent node ↔ Buzz agent mapping recorded at **role** level (§2); ephemeral workers map to nothing. | root (supplement 2A25343E, fold-ins i and ii) | **Approve.** The third sense had no word and was borrowing "fractal", which made §1's revocation rule, §2's identity scoping, and §4's grants ambiguous between a capability and a run — they read as nonsense applied to a run, so this is a correctness fix for a governing document, not style. The term did not need inventing: **capability** is exactly what the identity ruling above defines, so the vocabulary falls out of the rulings rather than being layered on. Fold-in (i) is the same statement seen from the other end — role-scoped identity *is* role-level agent mapping — and the observation that Buzz's flat agent model cannot represent a subgraph's internals is recorded as §6.1 holding accidentally, which is worth knowing but is not load-bearing for anything. |
