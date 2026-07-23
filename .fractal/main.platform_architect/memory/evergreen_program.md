---
name: evergreen_program
desc: Evergreen design pass — children, contracts, decision spaces, synthesis plan.
created: 2026-07-23T21:40:30Z
updated: 2026-07-23T21:40:30Z
---

# evergreen_program

## Directive

Root directive 7803C28A (saved in radio queue). Three deliverables:
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

Steer children each sync; merge settled children at PREPARE; rewrite README
as aggregate; write DESIGN.md §5 revision + §8 compaction advance +
decision-log rows (name requester = root directive 7803C28A, verdicts);
radio reply to root with tree/evergreen/NODE.md skeleton proposal; progress
summary priority 2-3; unsave 7803C28A; then node finish. If a child
straggles past my last iteration: synthesize what landed, note the gap in
aggregate + outbox, leave the rest for the next run (standing role).
