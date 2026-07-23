# Lindenmayer — Platform Design Manifest

- **Owner:** `main.platform_architect` (see `tree/platform-architect/NODE.md`).
  Changes to this document land only through the architect; rejections are a
  veto by default.
- **Status:** bootstrap draft, adopted from the root's initial sketch. Current
  truth lives in the body; history lives in the decision log; bulk research
  lives in `docs/research/`.

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
- Translates Fractal telemetry and radio into signed Buzz events as custom
  Nostr kinds, following Buzz's "new feature = new kind number" idiom and its
  NIP-AM / NIP-AO metric drafts.
- Maps tree structure onto Buzz primitives: Fractal nodes are git branches →
  Buzz's "branch as room" binds subgraphs to channels; channel membership is
  the only access gate.
- Node identity via NIP-OA owner attestation: each node's keypair is attested
  by its responsible human; revoking the human revokes the subgraph.
- Fractal `requires_approval` steps surface as signed Buzz approval events.

## 2. Identity (persistent nodes)

Fractal provides the graphs and subgraphs; connecting a node to Buzz is what
gives it an identity (an npub, attested per NIP-OA). Not all nodes need one —
only the persistent nodes central to executing work. Conceptually, persistent
nodes are like the "sub-agents" of coding harnesses: named, durable roles with
track records. Ephemeral worker nodes stay anonymous inside their subgraph;
their work reaches the record only as the aggregates their persistent parent
signs.

## 3. Node Templates (the improvable asset)

The unit of improvement is the **Node Template**, not the node instance. A
template contains system prompts, skills, files, and references, and defines
the context available to the node via tool calls. Templates are registered in
the registry as signed Buzz events, so every template is versioned,
attributable, and diffable; instances record which template version spawned
them, and evals attach to template versions. That linkage — instance → template
version → eval history — is what makes the workforce "versioned and
evaluated" rather than a pile of one-off prompts.

*(Registration mechanics — kind numbers, update/replace semantics, template
inheritance — are open; see §8.)*

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
   not a feature.
2. **No new storage systems.** The signed event log is the history. Retention
   is relay policy, per channel. Source-of-truth data stays in Fractal's
   SQLite and the Buzz relay; parquet files in `data/` are snapshot exports
   for local review (duckdb), never sources of truth.
3. **Never patch or fork Fractal.** Integrate only through its extension
   surfaces; add no capabilities to Fractal nodes.
4. **Human governance is explicit and traceable.** Design review is a veto by
   default (a platform parameter); disagreements resolve as recorded
   conversation, never silent override.

## 7. Development & demo strategy

- Developed by a Fractal tree from day one; the demo observes the tree that
  builds Lindenmayer, so dashboards show real subgraphs, merge-acceptance,
  and cost data.
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
- **Template registration mechanics.** Kind numbers, versioning/replace
  semantics (parameterized-replaceable vs. append-only), template
  inheritance, and what exactly an eval attaches to.
- **Custom kind allocation.** Lindenmayer's event kinds within Buzz's
  40000–49999 custom range; relationship to NIP-AM/NIP-AO drafts.
- **Retention policy defaults.** What per-channel relay retention ships as
  the privacy-preserving default.
- **Evals pillar.** Sketched only via hand-authored Completion Requirements;
  needs its own design pass once bridge events exist.
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
| 2026-07-23 | Evergreen continuity: compactions must map back to the task (run/iter/step) they summarize, as a trace to raw context. | root | Accepted as open design question (§7); noted in the architect's contract. |
| 2026-07-23 | This manifest bootstrapped from the root's design sketch (bridge, identity, templates, evergreen node, principles, dev/demo strategy). | root | Adopted as draft; §3 registration sentence completed by inference, pending root review. |
| 2026-07-23 | Provenance is a training asset (§4): the signed event log doubles as a labeled training corpus — filtering by acceptance, preference pairs from rejection→revision→acceptance chains, outcome/context conditioning, and versioned audit trails for debugging trained behavior. | root | Adopted; training extraction & consent added as open question (§8). |
| 2026-07-23 | History access grants (§4): humans grant time-limited history access — to a node or another human — for task/project fine-tuning, modeled as a signed, revocable, expiring event so consent has the same provenance as everything else. Hosted tuning infra (Baseten/Fireworks-type) is future development. | root | Adopted; resolves the consent-model half of the prior open question; grant mechanics remain open (§8). |
