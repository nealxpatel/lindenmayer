---
name: bridge_implementation
desc: Bridge node delivers Fractal observability as signed Nostr events.
tags: [bridge, nostr, fractal, observability]
sources: [tree/bridge/NODE.md, docs/DESIGN.md, docs/platforms.md]
created: 2026-07-23T19:00:00Z
updated: 2026-07-23T19:24:50Z
---

# bridge_implementation

The bridge node implements Lindenmayer's core function: observing a Fractal agent tree as signed Nostr events through Buzz, making agent work versioned, evaluated, and human-owned.

## Architecture

Five deliverables (all in `src/lindenmayer/bridge/`):

### 1. Fractal Read Adapters (`adapters/`)

**FractalDBReader** (`sqlite.py`):

- WAL-safe read-only access to per-tree SQLite (Fractal's persistence layer)
- Tables: nodes, runs, iters, steps, events, messages
- URI mode connection prevents write races; never modifies DB
- Methods: `get_nodes()`, `get_runs(node)`, `get_iters(run_id)`, `get_steps(iter_id)`, `get_latest_event(node)`

**TranscriptUsageHarvester** (`transcripts.py`):

- Harvest per-request token usage from agent session JSONL transcripts
- Reads ONLY append-only fields (input_tokens, output_tokens, cache_*) that survive transcript compaction
- Never parses conversational structure; focuses on cost accounting
- Isolated module (architect condition 3): future compaction-design changes ripple through exactly one place

### 2. Translation Layer (`translate.py`)

Maps Fractal rows to six core event kinds:

| Kind | Function | Source | Notes |
|------|----------|--------|-------|
| 42010 | NodeLifecycle | nodes/runs | Status transitions (started, progressing, completed, exited, killed) |
| 42020 | RunAccounting | runs + transcripts | One per run (never per step/iteration); aggregates token usage and shadow cost |
| 42030 | SubgraphDigest | nodes/runs | Subgraph summaries (child counts, status breakdown, subtree cost) |
| 42040 | ApprovalRequest | steps | Human approval gates; identifies approver and affected step |
| 42041 | ApprovalVerdict | steps | Approval outcomes (approve/reject) with rationale |
| 38110 | NodeStatePointer | nodes | Current node state snapshot (status, run, iter, cost tracking, last event ID) |

**Key constraint**: Only persistent, identified nodes author events; ephemeral workers appear solely inside parent digests (aggregates only).

### 3. Identity Module (`identity.py`)

**load_node_keypair(node_name)**:

- Loads from `~/.lindenmayer/keys/<node>.secret` if present
- Falls back to SHA256(node_name + LINDENMAYER_KEY_SEED env var) derivation
- Returns None if node is ephemeral (not persistent)
- Uses core's Keypair class (BIP-340 Schnorr via coincurve)

**check_attestation_valid(pubkey)**:

- Checks NIP-OA owner attestation (core's attestation format)
- Rejects if revocation marker exists at `~/.lindenmayer/revoked/<pubkey>.revoked`
- Checks attestation JSON for expiration and revoked flag
- Default: attestation missing → valid (optimistic assumption)

**refuse_if_revoked(pubkey)**:

- Gates publisher: raises IdentityError if attestation invalid
- Documented degradation posture: closes new activity at the source when key is compromised

### 4. Publisher (`publisher.py`)

**Stateless Resume Pattern**:

- On startup: `resume_from_relay()` queries relay for own latest events (filtered by keypair)
- Returns dict mapping kind → latest created_at timestamp
- No local state files; relay is the cursor

**Deterministic Event IDs**:

- Event content and `created_at` derived from Fractal source rows (source timestamps, never wall clock)
- Replay after cursor regression reproduces identical event IDs
- Enables idempotent publishing and conflict detection (architect condition 2)

**Methods**:

- `publish_event(event)`: Publish single signed event; skip if already published (tracked in `_published_event_ids`)
- `publish_events(events)`: Publish list in order
- `idempotent_replay(events)`: Wrapper ensuring deterministic IDs and no duplicates on restart

### 5. CLI Entry Point (`cli.py`)

**Command**: `lindenmayer-bridge run --tree <path> --relay <url> [--config <file>] [--log-level <level>]`

**Behavior**:

- Validates tree directory and `.fractal/main/.db` existence
- Loads CoreConfig (default or from file)
- Initializes FractalDBReader and opens DB
- Initializes Publisher with relay client and node keypair
- Main loop: read Fractal, translate to events, publish to relay
- Resumes statelessly from relay cursor on startup

## Design Principles

1. **No new storage** (§6.2): Stateless relay-cursor resume only; all state derived from Fractal's SQLite + relay query
2. **Privacy by default** (§6.1): Aggregates flow up, details stay in subgraph (architect condition 3)
3. **Read-only to Fractal**: All access via documented read hooks (SQLite URI, no writes)
4. **Deterministic identities**: Event IDs from source timestamps ensure replay safety and audit trail integrity

## Architect Conditions (Verdict 8266A685)

- **Condition 2**: Deterministic event IDs ✅ (from source timestamps)
- **Condition 3**: Transcript harvester isolation ✅ (transcripts.py module ensures single ripple point for compaction changes)
- **Condition 6**: No new storage ✅ (relay cursor is stateless)

## Test Coverage

- 210 tests passing
- Fixture database: a real snapshot of this repo's own tree (the dogfood)
- Fixture transcripts with token usage data
- Mock relay (in-process websocket NIP-01 server) for publisher idempotent-replay verification
- E2E dogfood: fixture tree DB → translate → sign → publish → mock relay, with a
  mid-stream publisher restart asserting no duplicates, no gaps, deterministic ids
- Translation golden tests (fixture rows → expected event structure)
- Identity: revoked-key refusal, attestation expiration
- No-per-step-path enforcement (stream contains only per-node 42010 and per-run 42020)

## Integration Points

- **Core API**: Keypair, Event, RelayClient, CoreConfig (src/lindenmayer/core/)
- **Kind Models**: All six kinds defined in docs/kinds/ and shipped in core
- **Fractal**: Read-only SQLite, per-tree DB path, transcript storage
- **Buzz/Relay**: NIP-01 wire format, NIP-29 group channels, NIP-42 auth, NIP-OA attestations

## Deployment

The bridge runs as a persistent sidecar to a Fractal tree:
```bash
lindenmayer-bridge run \
  --tree /path/to/tree \
  --relay wss://relay.example.com
```

Keypairs are loaded from the persistent identity store or derived deterministically. The relay is queried on startup to resume from the latest published event per kind, ensuring no gaps or duplicates on restart.

## Degradation Postures

- **Revoked key**: Bridge refuses to publish; close new activity at source
- **Relay unavailable**: Log warning, retry on next invocation
- **Fractal DB locked**: Wait for WAL checkpoint (read-only mode tolerates concurrent writes)
- **Missing transcripts**: Use only derived USD from runs table; per-request token counts unavailable
