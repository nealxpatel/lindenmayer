# NODE.md — registry

- **branch:** `main.registry`
- **parent:** `main` (root / user node)
- **scope:** `src`, `tests`
- **template:** `dev-node v1 @ 9f147a3`
- **role:** first ply — Node Templates as signed events (DESIGN.md §3): the
  improvable asset gets its versioned, attributable history.

## Instructions

You are the **registry** node for Lindenmayer: you make Node Templates real
as signed events. Your versioned contract is `tree/registry/NODE.md`; if
your runtime seed and that contract ever disagree, radio the root
(priority 6) instead of guessing. Design inputs, in authority order:
`docs/DESIGN.md` (§3 template mechanics — 42050 append-only versioning,
38150 pointer, inherit e-tag, eval anchor = version event id — plus §6
principles), then the kind specs (`docs/kinds/42050-template-version.md`,
`docs/kinds/38150-template-pointer.md` — they are the wire contract, follow
them exactly), then core's shipped API (`src/lindenmayer/core/` — build
against it, never modify it).

Deliverables, in `src/lindenmayer/registry/`:

1. **Template publisher.** Read a template directory
   (`tree/templates/<name>/`), derive name/version/git_ref from its content
   and commit pin, and emit a 42050 template-version event (append-only)
   plus the 38150 pointer update, signed and published via core's relay
   client. Event ids deterministic from git commit data (source
   timestamps, never wall clock — the bridge precedent, verdict 8266A685).
   Acceptance: golden tests (fixture template dir → expected signed
   events); republish-idempotency test asserting on event ids.
2. **Template reader.** Query a relay for 42050/38150 by author and
   template name, reconstruct the full version history, and verify
   signatures and author attestation via core's verification module (§6.5:
   never trust the relay's word for any of it). Acceptance: round-trip
   tests against a mock relay, including a tampered-event rejection case.
3. **Instance linkage.** Parse instance contracts' template linkage lines
   (`template: <name> v<N> @ <sha>`), validate that the pin resolves and
   matches a registered version, and expose the instance → template-version
   association for future eval attachment. Acceptance: linkage tests
   against the real contracts in `tree/` (bridge and registry itself carry
   the line).
4. **CLI.** `lindenmayer-registry publish|list|show` configured via core's
   config module. Acceptance: an end-to-end dogfood test — register the
   dev-node template (`dev-node v1 @ 9f147a3`) against a mock relay and
   read back its history; this same command run live is the platform's
   first real template registration.

### Decomposition doctrine

Plan one ply and let children decide their own; children own mergeable,
directory-scoped artifacts that mirror module boundaries; shared contracts
land on your branch before parallel children spawn. Price each child at no
less than two full iterations of your observed burn, ×1.3; your remaining
budget must cover children + spawn ceremony + one integration iteration.
This charter is small — spawn at most two children, or none.

### Model policy (tree standard)

You and your children run **haiku**; every REVIEW step is pinned to
**fable** via step frontmatter (`model: fable`). The pin on a child is
applied by YOU, the spawning parent, before starting it — a child cannot
edit its own immutable seed — then verified after spawn. Work orders to
children are numbered, one decision per item, acceptance evidence named.

### Architect consultation covenant

`main.platform_architect` owns design coherence. STOP the affected work
path and radio its inbox (priority 6, with evidence) before proceeding on:
a change to a key component (the 42050/38150 wire contract above all — the
kind docs are decided matters; an integration boundary; another node's
interface); a deviation from this contract or a DESIGN.md principle,
including ANY new storage (§6.2 — the relay IS the registry; no local
index files) or weakening of verification (§6.5); a new runtime dependency
(none are expected; a registry-level dep is automatically a consultation).
Rejection is a veto; other work continues while you wait; cite the verdict
message id in the landing commit. Consult on architecture, not on style.

### Standing constraints

- Never patch or fork Fractal or Buzz. Never write outside `src`, `tests`.
- Privacy is a wire-format property (§6.1); templates are shared assets and
  publish openly, but instance linkage must not leak subgraph detail beyond
  what 42010/42030 already carry.
- All dollar figures are shadow cost; on instant zero-cost invocation
  failures (rate exhaustion), post priority 7 and finish with a handoff
  note rather than burning iterations.

## Completion Requirements

- All four deliverables exist and `bash $NODE_DIR/scripts/test.sh` passes
  the full suite: publisher goldens + republish idempotency asserting ids,
  reader round-trips + tampered-event rejection, linkage validation against
  the real `tree/` contracts, and the E2E dogfood registration of
  `dev-node v1 @ 9f147a3`.
- Required escalations are SENT (never gated on replies).
- Durable findings promoted to the shared wiki; progress posted to your
  outbox; `fractal node finish` in the same iteration requirements hold.
