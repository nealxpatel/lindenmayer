# Evergreen design pass — research aggregate (in progress)

Working aggregate for the evergreen-component design pass (root directive
7803C28A). Research children are in flight; this file currently holds the
architect's decision framing and will be rewritten into the final aggregate
once the studies land. Child studies (each owned by its node):

- `compaction.md` — compaction observability, harvester boundary, task
  anchors, Nostr derived-view prior art (`main.platform_architect.compaction`).
- `inventory.md` — requirements inventory from `tree/root/CONTEXT.md`,
  classified by data source, mapped to §5's four capabilities
  (`main.platform_architect.evergreen_inv`).
- `buzz-surface.md` — Buzz primitives, ingest constraints, identity, per-kind
  cross-post mapping (`main.platform_architect.buzz_surface`).

## Decision spaces (architect's framing, ahead of findings)

### 1. Compaction-to-task mapping (DESIGN.md §8)

The question: a compacted evergreen-session summary is a derived view; how
does it keep a pointer to its source (run/iter/step → raw transcript)?

Constraints fixed before any candidate is weighed:

- **Evals fence.** Anything eval-shaped waits for the evals pillar. A
  compaction pointer is provenance, not evaluation — if a candidate shape
  starts wanting scores, verdicts, or quality labels, it is out of bounds.
- **Single-module blast radius.** Bridge condition 3 (verdict 8266A685)
  isolated all transcript parsing behind one harvester adapter precisely so
  this resolution ripples through one module. A candidate that needs parsing
  logic anywhere else fails.
- **§6.1 no-leak.** The pointer maps summary → task coordinates → raw
  transcript *within the subgraph*. What flows up is at most the fact and
  coordinates of a compaction, never summarized content of a private
  subgraph. (For this dev tree, transcripts are published by the §7 opt-in —
  but the design must hold under the platform default, private-in-subgraph.)

Decision axes the candidates must be scored on: wire-visible event vs
tag-on-existing-kind vs documented convention; whether the pointer is written
at compaction time (harvest) or reconstructed at read time; and what happens
when a summary spans multiple runs/iterations.

### 2. Evergreen v1 (DESIGN.md §5)

What evergreen IS at first ship. The candidate framings to be settled by the
inventory findings:

- (a) a **generator/maintainer of the context surface** — produces and
  refreshes what `tree/root/CONTEXT.md` is by hand today;
- (b) a **query CLI over the relay's event log** — answers the questions the
  root currently answers by reading files and radio;
- (c) both, with (b) feeding (a).

The v1 line through the four §5 capabilities (commission, steer, review
approvals, query own history) gets drawn against the inventory's
exists-today/gap map. Prior: capabilities that reduce to *reading the signed
log* are cheap and §6.2-clean; capabilities that *act* on the tree
(commission, steer) already exist as Fractal operator surfaces and may enter
v1 as documented pointers rather than new machinery — evergreen adds no
capabilities to Fractal nodes (§0), it makes existing primitives durable and
observable.

### 3. Buzz human surface (DESIGN.md §1)

Fixed invariants (restated, not open): Buzz is the human surface, never the
core-log carrier (D35D86E8); cross-posts are derived views — publish-time
`created_at`, source timestamp + core event id in tags, deduplicated by that
reference; identity is NIP-OA owner-attested. The open design choices, to be
grounded by the buzz-surface findings: which event families cross-post in v1,
into which channel shapes (subgraph channel vs approvals inbox), and what the
human does in Buzz vs in evergreen's own surface.

## Outputs of this pass (when research lands)

1. This README rewritten as the aggregate (the interface for the contract
   draft).
2. DESIGN.md §5 revision + §8 compaction resolution/advance + decision-log
   rows.
3. Proposed `tree/evergreen/NODE.md` deliverable skeleton, sent to the root
   by radio (tree/ is the root's to edit).
