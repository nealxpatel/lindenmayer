---
name: evergreen_program
desc: Evergreen design pass — children, contracts, decision spaces, synthesis plan.
created: 2026-07-23T21:40:30Z
updated: 2026-07-23T21:40:30Z
---

# evergreen_program

## Status

All three research children are COMPLETED (compaction, evergreen_inv,
buzz_surface). No child outstanding; the pass is integration + synthesis
only, plus one open review. Deliverables sit on the child branches
(`docs/research/evergreen/{compaction,inventory,buzz-surface}.md`) and land
at PREPARE. `docs/research/evergreen/README.md` is still the pre-research
working draft — rewriting it to the final aggregate is a hard gate before
finish.

## Open review: model-policy retiering (A6BE089F, saved)

Root directive, not a request, but a key-component change (dev-node template
+ tree-wide policy), so it needs a verdict and a decision-log row. Applied
state: REVIEW and this node run opus (was fable); dev nodes and children run
sonnet (was haiku); orchestrator opus. `tree/templates/dev-node` bumped to
v2 and registered as a signed 42050 (version event 0f8d0910, pin c6696b7) —
the registry's first real version bump.

Verdict direction (posted early to root as 05237766): APPROVE. It tunes an
economic parameter; it touches none of the four review-bar principles.
Corrections that must land with the row:

- `docs/DESIGN.md:108` names the tiers literally
  ("haiku-develop/fable-review model policy") — stale against the live tree.
  Rewrite to the SHAPE invariant (orchestrator writes precise work orders,
  cheaper tier executes, stronger tier reviews) with the current tier
  assignment recorded as a parameter, so the next retiering is a parameter
  edit and not a manifest contradiction.
- §7 decomposition economics were never load-bearing on haiku specifically —
  the doctrine's claim is a RATIO (execution cheaper than review and
  orchestration), which sonnet-develop/opus-review preserves. What changes is
  absolute burn per child, so derived cap-sizing guidance is stated against
  haiku-era numbers. Flag it; do not invent replacement numbers.
- §3 describes registry-backed template versions as future; they are live
  today. Update.

## Directive

Root directive 7803C28A (saved in radio queue), continued by A280F6DC.
Three deliverables:
(1) resolve/advance §8 compaction-to-task mapping, (2) design evergreen v1
concretely (requirements inventory = tree/root/CONTEXT.md; v1 line through
§5's four capabilities), (3) map the Buzz human surface. Outputs:
docs/research/evergreen/ aggregate README, DESIGN.md §5 revision with §8
update and decision-log rows, proposed tree/evergreen/NODE.md skeleton in my radio
reply to root (tree/ is root's to edit). Constraints owned: evals fence
(anything eval-shaped waits); harvester-adapter single-module blast radius
(my 8266A685 condition 3); §6.1 no-leak on compaction pointers. Relay at
ws://localhost:7100 is interim ops carrier (root FYI 5E37772F), not a relay
selection — §8 selection question stays open and mine.

## Children (all haiku leaves, $4 cap, $1.5/iter, 3 iters, scope docs/, trimmed steps PLAN+EXECUTE+COMMIT)

- `main.platform_architect.compaction` → owns
  docs/research/evergreen/compaction.md. Compaction records in
  transcripts/*.jsonl, harvester adapter surface, run/iter/step anchors
  (SQLite + 42010/42020 tags), Nostr derived-view prior art, 2-3 candidate
  shapes vs my three constraints. No kind allocation (mine).
- `main.platform_architect.evergreen_inv` → owns
  docs/research/evergreen/inventory.md. CONTEXT.md requirements table
  classified relay-derivable / fractal-derivable / human-authored; existing
  bridge/registry CLI query surfaces; per-capability gap list.
- `main.platform_architect.buzz_surface` → owns
  docs/research/evergreen/buzz-surface.md. Buzz primitives (NIP-29 rooms,
  inboxes, directory), ingest gate re-verified at current HEAD, NIP-OA
  handling, per-kind-family cross-post mapping table. Cites file@commit.

All self-finish on own committed deliverable + priority-3 outbox note;
friction escalates to me at priority 6. Spawned from my branch at commit
6968e84 (post parent-merge: contains docs/kinds/, merged bridge+registry
src, relay-integration aggregate).

## My decision framing

Drafted in docs/research/evergreen/README.md (decision spaces: compaction
constraints + axes; v1 framings a/b/c — generator vs query CLI vs both;
Buzz-surface fixed invariants vs open choices). README is a working draft
labeled in-progress; MUST be rewritten to final aggregate before finish
(narrative surfaces never advertise unwritten sections).

## Synthesis plan

No steering left — merge all three settled children at PREPARE; rewrite README
as aggregate; verdict + row on the model-policy retiering (above); write DESIGN.md §5 revision + §8 compaction advance +
decision-log rows (name requester = root directive 7803C28A, verdicts);
radio reply to root with tree/evergreen/NODE.md skeleton proposal; progress
summary priority 2-3; unsave 7803C28A, A280F6DC, C2CDCD79, A6BE089F; then
node finish. All research inputs are in hand, so no child-straggler
contingency applies.
