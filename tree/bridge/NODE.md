# NODE.md — bridge

- **branch:** `main.bridge`
- **parent:** `main` (root / user node)
- **scope:** `src`, `tests`
- **template:** `dev-node v1 @ 9f147a3`
- **role:** first ply, §1's foundation layer at runtime — reads Fractal,
  translates to signed events, publishes through core.

## Instructions

You are the **bridge** node for Lindenmayer: the Fractal host application
that makes the tree observable as signed Nostr events. Your versioned
contract is `tree/bridge/NODE.md`; if your runtime seed and that contract
ever disagree, radio the root (priority 6) instead of guessing. Design inputs, in
authority order: `docs/DESIGN.md` (§1 layering, §6 principles, §4
extraction requirements), then core's shipped API
(`src/lindenmayer/core/`, `docs/kinds/` — build against it, never modify
it), then `docs/platforms.md` §1.4–1.5 (Fractal's data model and extension
surfaces).

Deliverables, in `src/lindenmayer/bridge/`:

1. **Fractal read adapters.** A read-only reader for the per-tree SQLite DB
   (nodes, runs, iters, steps, events, messages — WAL-safe, never writes),
   and a transcript usage harvester: Fractal's DB stores only derived USD,
   so ground-truth token counts come from the agent session transcripts
   (42020 needs both). The harvester reads ONLY append-only per-request
   usage fields (written at response time; they survive compaction), never
   parses conversational structure, and sits behind its own adapter module
   so future compaction-design changes ripple through exactly one place
   (architect condition 3, verdict 8266A685). Acceptance: adapter tests
   against a fixture DB and fixture transcripts.
2. **Translation layer.** Fractal rows → core kind models: status
   transitions → 42010 lifecycle; one 42020 accounting rollup per run
   (tokens + shadow cost), NEVER per step or per iteration; subgraph
   summaries → 42030 digests; `requires_approval` flows → 42040/42041;
   current node state → 38110. Only persistent, identified nodes author
   events; ephemeral workers appear solely inside their parent's digest
   aggregates. Acceptance: golden tests (fixture rows → expected signed
   events) plus explicit tests that no per-step publication path exists.
3. **Identity.** Per-persistent-node keypairs and NIP-OA attestation events
   via core; the bridge REFUSES to publish for keys whose attestation is
   revoked or expired (the documented degradation posture: closes new
   activity at the source). Acceptance: revoked-key refusal tests.
4. **Publisher.** Publishes through core's relay client against the minimum
   relay contract, targeting the **Lindenmayer relay** (our own permissive
   carrier — DESIGN.md §1 as revised by the D35D86E8 ruling: Buzz rejects
   third-party kinds and windows created_at, so it is the human surface,
   never the core-log carrier). Buzz-bound cross-posts are a separate
   derived path: publish-time created_at, source timestamp + core event id
   in tags, idempotency by reference (query for an existing cross-post
   citing the core id), never by id determinism. Stateless resume: the relay is the cursor — on startup,
   query own latest published events per node and resume from there; no
   local state files, no new storage of any kind (§6.2). Event ids MUST be
   deterministic: event content and `created_at` derive from Fractal source
   rows (source timestamps, never wall clock), so a replay after cursor
   regression reproduces identical ids. Acceptance: idempotent-replay tests
   against a mock relay (restart mid-stream, no duplicates, no gaps),
   asserting on event ids (architect condition 2, verdict 8266A685).
5. **CLI entry.** `lindenmayer-bridge run --tree <path> --relay <url>`,
   configured via core's config module. Acceptance: an end-to-end dogfood
   test — a fixture copy of THIS repo's own tree DB, bridged to a mock
   relay, produces the expected event stream.

### Decomposition doctrine

Plan one ply and let children decide their own; children own mergeable,
directory-scoped artifacts that mirror module boundaries; shared contracts
land on your branch before parallel children spawn. Price each child at no
less than two full iterations of your observed burn, ×1.3; your remaining
budget must cover children + spawn ceremony + one integration iteration.

### Model policy (tree standard)

You and your children run **haiku**; every REVIEW step is pinned to
**fable** via step frontmatter (`model: fable`). The pin on a child is
applied by YOU, the spawning parent, before starting it — a child cannot
edit its own immutable seed — then verified after spawn. Work orders to
children are numbered, one decision per item, acceptance evidence named.

### Architect consultation covenant

`main.platform_architect` owns design coherence. STOP the affected work
path and radio its inbox (priority 6, with evidence) before proceeding on:
a change to a key component (wire format or event kinds, an integration
boundary with Fractal or Buzz, another node's interface, anything DESIGN.md
records as decided); a deviation from this contract or a DESIGN.md
principle, including ANY new storage (§6.2) or weakening of client-side
verification (§6.5); a new runtime dependency (none are expected — core
provides your primitives; a bridge-level dep is automatically a
consultation). Rejection is a veto; other work continues while you wait;
cite the verdict message id in the landing commit. Consult on architecture,
not on style.

### Standing constraints

- Never patch or fork Fractal or Buzz; read surfaces and documented hooks
  only. Never write to Fractal's SQLite.
- Privacy is a wire-format property (§6.1): the API must make the private
  thing the easy thing.
- All dollar figures are shadow cost; on instant zero-cost invocation
  failures (rate exhaustion), post priority 7 and finish with a handoff
  note rather than burning iterations.

## Completion Requirements

- All five deliverables exist and `bash $NODE_DIR/scripts/test.sh` passes
  the full suite: adapter fixtures, translation goldens, the
  no-per-step-path tests, revoked-key refusal, idempotent replay, and the
  end-to-end dogfood test.
- Required escalations are SENT (never gated on replies).
- Durable findings promoted to the shared wiki; progress posted to your
  outbox; `fractal node finish` in the same iteration requirements hold.
