# Compaction-to-Task Mapping Research

> **Architect note — one finding in this study is superseded.** §1's
> conclusion that "no compaction record exists today," and the next-step that
> follows from it (asking Claude Code to emit one), are incorrect: the harness
> already writes a `system` record carrying `compactMetadata`. The adopted
> design reads that marker. See `README.md` §1 for the corrected version and
> the measurements behind it. The rest of this study — harvester boundary,
> task anchors, Nostr referencing idioms, candidate comparison — stands, and
> its Candidate A shape is what shipped.

**Research Question:** How should evergreen-session compactions map back to the task they summarize? (DESIGN.md §8, "Compaction-to-task mapping")

**Constraint Framework:**
- **(a) Evals fence:** No eval-shaped machinery, no kind-number allocation outside the 381xx/420xx blocks already committed to. New events labeled "kind TBD by architect."
- **(b) Single-module blast radius:** Any resolution implementable inside `src/lindenmayer/bridge/adapters/transcripts.py` alone.
- **(c) Privacy (§6.1):** Compaction pointers must not leak subgraph detail upward—aggregates up, details stay in the subgraph.

---

## 1. Compaction Observability

### Current State: What Transcripts Record

**Transcript Structure.** Transcripts are append-only JSONL files (one record per line) stored in `transcripts/*.jsonl`. Each record is a JSON object with a `type` field identifying the record category. Observed types include:
- `queue-operation`: enqueue/dequeue events
- `user`: user messages with role, content, uuid, parentUuid, sessionId
- `attachment`: tool listings, deferred schemas
- `cost`: per-request token usage (the only records preserved through compaction)

**Worked Example** (`3a8a6eda-08e1-4f14-a9a5-e6475a8cb01c.jsonl` @ 2026-07-23T18:06:24Z):
```json
{
  "type": "cost",
  "timestamp": "2026-07-23T18:06:24.201Z",
  "sessionId": "3a8a6eda-08e1-4f14-a9a5-e6475a8cb01c",
  "model": "claude-opus-4-8",
  "usage": {
    "input_tokens": 1245,
    "output_tokens": 567,
    "cache_creation_input_tokens": 0,
    "cache_read_input_tokens": 0
  }
}
```

**Compaction Behavior.** As documented in `src/lindenmayer/bridge/adapters/transcripts.py:1–8`:
> Reads ONLY append-only per-request usage fields (written at response time; they survive compaction), never parses conversational structure.

Claude Code automatically compacts long-running sessions by summarizing the conversational context. The compaction process:
1. Summarizes earlier messages into a compressed context
2. Removes individual message records from the transcript
3. Preserves cost events (written at request completion, append-only)

**Finding: No Compaction Record Exists Today.** Transcripts contain no explicit "compaction" record type or marker. When a compaction occurs, there is no signed artifact in the transcript identifying:
- What span was compacted (message IDs, timestamp range, or run/iter/step coverage)
- What the compaction summary is or where it points
- Whether this is a compaction or a gap

The adapter's documentation anticipates this gap: "changes to compaction design ripple through exactly one place," but the design itself is not yet in place.

---

## 2. Harvester Boundary

### Current Adapter Interface

**Module:** `src/lindenmayer/bridge/adapters/transcripts.py`

**Current Read Surface:**
- `iter_requests()` — yields dict with keys: `model`, `input_tokens`, `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`
- `get_total_usage()` — sums all requests, returns aggregated dict

**Design Intent:** The module is "isolated behind its own module so future compaction-design changes ripple through exactly one place" (architect ruling, verdict 8266A685 in source comment).

### Proposed Minimal Extension

To harvest compaction-to-task mappings without breaking the isolation rule (constraint b), a compaction-pointer harvester would:

1. **Read Surface Addition:** Extend the adapter with a new method:
   ```python
   def iter_compactions(self):
       """Iterate over compaction records in the transcript.
       
       Yields dicts with keys:
       - timestamp: ISO 8601 timestamp of compaction event
       - span_start_ts: timestamp or record-count marking the start of compacted span
       - span_end_ts: timestamp or record-count marking the end
       - summary_hash: hash of the compacted summary text (for dedup)
       - source_run: run_id from Fractal DB (optional; harvested via session lookup)
       - source_iter: iter_id from Fractal DB (optional)
       - source_step: step_id from Fractal DB (optional)
       """
   ```

2. **Transcript Record Type:** Require Claude Code to emit a new transcript record type when compaction occurs:
   ```json
   {
     "type": "compaction",
     "timestamp": "2026-07-23T20:15:17.000Z",
     "sessionId": "3a8a6eda-08e1-4f14-a9a5-e6475a8cb01c",
     "span_start_ts": "2026-07-23T18:06:24.000Z",
     "span_end_ts": "2026-07-23T20:15:00.000Z",
     "summary_hash": "sha256:<hash>"
   }
   ```

3. **Session-to-Task Lookup:** The adapter would read a manifest (e.g., `.fractal/session_manifest.json`) mapping `sessionId` → `(run_id, iter_id, step_id)` to enrich compaction records. This lookup file is written by Fractal at step start and survives across iterations.

**Design Benefit:** All compaction-pointer logic lives in one module. Bridge code calls `transcripts.iter_compactions()` without knowing the source (transcript file or fallback manifest). Changes to the compaction record schema only touch this file.

**Constraint Satisfaction:**
- **(b):** All parsing and enrichment inside one adapter ✓
- **(c):** Compaction pointers carry only timestamps, hashes, and Fractal IDs—no message content or subgraph state leaks ✓

---

## 3. Task Anchors

### Fractal's Identifier Hierarchy

**SQLite Schema** (`src/lindenmayer/bridge/adapters/sqlite.py`):

| Table | Columns | Purpose |
|-------|---------|---------|
| `nodes` | node_id, node, status, created_at | Persistent node registry |
| `runs` | run_id, node, parent_run_id, status, started_at, ended_at | One per `fractal node start` |
| `iters` | iter_id, run_id, iter (counter), **session**, status, started_at, ended_at | One per loop iteration; session = Claude Code UUID |
| `steps` | step_id, iter_id, run_id, step_name, status, started_at, ended_at | One per PLAN/EXECUTE/COMMIT/etc. |
| `events` | event_id, node, **step_id, iter_id, run_id**, event, status, created_at | Published events linked to task hierarchy |

**Key Finding:** The `iters` table carries `session` (Claude Code session UUID). A compaction record with sessionId can be looked up to find its iter_id, then traced to run_id and step_id.

### Existing Event Kinds and Tag Vocabulary

**Published Events** (kinds 420xx / 381xx):
- **42010 (Node Lifecycle):** tags `branch`, `status`, `run`, `p` (parent pubkey), `e` (previous lifecycle event)
- **42020 (Run Accounting):** tags `branch`, `run`, `template`
- **42030 (Subgraph Digest):** tags `branch`, `period_start`, `period_end`
- **42040/42041 (Approval):** tags `branch`, `run`, `request_id` / `verdict_id`
- **42050 (Template Version):** tags `template_name`, `version`, `git_ref`
- **38110 (Node State Pointer):** addressable, tags `branch`, `d` (identifier)
- **38150 (Template Pointer):** addressable, tags `name`, `version`

**Observation:** Existing kinds use `run` (run_id) as the primary task anchor. No kind yet carries iter_id or step_id.

**NIP-OA Attestation Tag:** Already defined in `docs/kinds/nip-oa-attestation.md`. Includes `auth` tag with owner pubkey, conditions, and BIP340 signature. Not relevant to compaction pointers (which are derived views, not authorization events).

---

## 4. Nostr Prior Art: Event Referencing Idioms

### Standard Nostr Event Reference Patterns

**NIP-10 (Nostr Event References):** Defines `e` and `p` tags for event/person references. The `e` tag optional third element is a **marker**:
- No marker: relay-hint for backwards compat
- `reply`: this event is a reply to the referenced event
- `root`: this event is in a reply-thread rooted at the referenced event
- `mention`: this event mentions the referenced event (NIP-08)

**NIP-18 (Quote Reposts):** Uses `q` tag for a quoted event:
```json
{
  "tags": [
    ["q", "<event-id>", "<relay-url>"]
  ]
}
```
Semantics: this event is a repost/quote of the event identified by event-id. The relay URL is optional.

**NIP-51 (Lists):** Uses `e` tags with markers to categorize list items:
```json
{
  "tags": [
    ["e", "<event-id>", "<relay>", "item-type"],
    ["d", "<list-identifier>"]
  ]
}
```

**Marker Pattern:** The third field of a tag can carry a **marker** string to indicate the relationship type. Example: `["e", "<id>", "<relay>", "summary-of"]` would indicate "this event is a summary of <id>".

### Application to Compaction Mapping

**Option 1: `e` tag with `summary-of` marker**
```json
{
  "tags": [
    ["e", "<step-event-id>", "", "summary-of"]
  ]
}
```
Reads: "This compaction event is a summary of the event with id step-event-id." The marker `summary-of` is a Lindenmayer-specific convention (not standardized) but follows the NIP-10 pattern.

**Option 2: `q` tag (Quote Repost style)**
```json
{
  "tags": [
    ["q", "<step-event-id>"]
  ]
}
```
Reads: "This is a derived/quoted view of the referenced event." Lighter than Option 1 but less semantic (quote reposts traditionally carry a comment; a compaction summary is not a quote).

**Option 3: Composite tag with Fractal IDs**
```json
{
  "tags": [
    ["run", "run-001"],
    ["iter", "5"],
    ["step", "EXECUTE"],
    ["compaction-span-start", "2026-07-23T18:06:24Z"],
    ["compaction-span-end", "2026-07-23T20:15:00Z"]
  ]
}
```
Reads: A set of tags directly carrying Fractal identifiers (run_id, iter_id, step_name, timestamps). No event-id reference, instead explicit task coordinates.

---

## Candidate Mapping Shapes

### Candidate A: Compaction Event Kind (kind TBD)

**Form:** A new kind (number TBD by architect, tentatively in the 420xx block per §3) published as a periodic or end-of-session summary.

**Schema (Draft):**
```json
{
  "kind": "TBD",
  "tags": [
    ["branch", "<node-branch>"],
    ["run", "<run-id>"],
    ["iter", "<iter-id>"],
    ["step", "<step-name>"],
    ["compaction-session", "<claude-code-session-uuid>"],
    ["compaction-span-start", "<iso8601-ts>"],
    ["compaction-span-end", "<iso8601-ts>"],
    ["e", "<step-event-id>", "", "summary-of"]
  ],
  "content": "{\"iter_count\":1,\"duration_s\":3600.0,\"context_tokens_compacted\":125000,\"summary_hash\":\"sha256:<hash>\"}"
}
```

**Semantics:** One event per compaction. Tags carry Fractal task coordinates and the span of time/records compacted. The `e` tag with `summary-of` marker points back to the step's lifecycle event. Content holds metrics.

**Tradeoffs:**
- ✓ **Discoverable:** Querying kind TBD finds all compactions for a node
- ✓ **Verifiable:** Signed by the node (same attestation as other events)
- ✓ **Linked:** The `e` tag creates a Nostr-native reference to the source task
- ✗ **New kind number:** Requires architect allocation (constraint a violation; marked "kind TBD")
- ✗ **Repetitive:** For highly compacted sessions, may emit many events (one per compaction)
- ✓ **Privacy:** Contains only aggregate metrics, task IDs, timestamps—no conversational content

**Constraint Compliance:**
- **(a):** Kind TBD, no evaluation infrastructure ✓
- **(b):** Bridge harvests via adapter.iter_requests() + adapter.iter_compactions() ✓
- **(c):** No subgraph detail leaked (only task IDs and metrics) ✓

---

### Candidate B: Compaction Pointer Tags on Step Lifecycle Event

**Form:** When a step completes, if the step's iter was compacted, attach tags to the step's 42010 lifecycle event retrospectively (or emit a supplementary 42010 lifecycle event marking the compaction).

**Schema (on 42010 event):**
```json
{
  "kind": 42010,
  "tags": [
    ["branch", "main.evergreen"],
    ["status", "completed"],
    ["run", "run-001"],
    ["compaction-metadata", "{\"session\":\"<uuid>\",\"span_start\":\"<ts>\",\"span_end\":\"<ts>\",\"hash\":\"<hash>\"}"]
  ],
  "content": "{\"reason\":\"Step EXECUTE completed\"}"
}
```

Alternatively, emit a supplementary 42010 event with status = "context-compacted":
```json
{
  "kind": 42010,
  "tags": [
    ["branch", "main.evergreen"],
    ["status", "context-compacted"],
    ["run", "run-001"],
    ["e", "<previous-lifecycle-event-id>"]
  ],
  "content": "{\"session\":\"<uuid>\",\"span_start\":\"<ts>\",\"span_end\":\"<ts>\"}"
}
```

**Semantics:** Metadata is embedded as a JSON tag value or as a new status value in the existing kind. No new kind.

**Tradeoffs:**
- ✓ **No new kind:** Uses existing 42010 (constraint a compliant)
- ✓ **Tightly linked:** Compaction metadata lives on the step it describes
- ✗ **Retrofitting problem:** If a step completes before compaction, the event must be amended or supplemented after-the-fact (violates immutability in some interpretations)
- ✗ **Tag pollution:** Adding domain-specific JSON to tags muddies the kind's contract
- ✓ **Privacy:** Same as Candidate A

**Constraint Compliance:**
- **(a):** Uses existing kind ✓; but JSON-in-tag is fragile
- **(b):** Adapter harvests tags from iters table, matches session to event ✓
- **(c):** No subgraph detail ✓

---

### Candidate C: Compaction Doc-Only Convention (Descriptor in Project Wiki)

**Form:** No new events. Compaction metadata is recorded as a structured doc (e.g., `docs/compaction-manifest.md` or per-node manifest in `tree/evergreen/.compactions/`) describing the mapping:
```
run-001, iter 5, EXECUTE: session=3a8a6eda, compacted 2026-07-23T18:06:24Z–2026-07-23T20:15:00Z
```

The mapping is **versioned in git**, not published to Nostr. The evergreen node reads this doc at startup to reconstruct the span.

**Semantics:** Compaction metadata is a project artifact (git-tracked, human-readable), not a signed event. The bridge checks this doc when harvesting compaction data.

**Tradeoffs:**
- ✓ **Simple:** No new Nostr machinery
- ✓ **Audit trail:** Git history shows when mappings were added
- ✗ **Not signed:** No cryptographic proof of compaction provenance (someone could forge the doc)
- ✗ **Privacy violation risk:** If this doc is part of the repo and the repo is public, it leaks the evergreen node's full task history (constraint c at risk)
- ✗ **Offline discovery:** A client can't query the relay for "give me compactions for this node"; must pull the repo
- ✗ **Cross-subgraph opacity:** Other nodes can't independently verify the mapping; must trust the doc

**Constraint Compliance:**
- **(a):** No new events ✓
- **(b):** Adapter can read from a git-tracked manifest file ✓; but violates the "transcript-sourced" intent
- **(c):** High risk—publicly exposing the compaction history of an evergreen node is a privacy leak. Only tenable if the repo is private-in-subgraph and never published

---

## Recommendation

**Candidate A (Compaction Event Kind)** is the strongest fit:

1. **Traceability:** Signed, timestamped events create an immutable audit trail. A client can query the relay: "show me all compactions for node X" and verify the chain cryptographically.

2. **Modular:** Harvesting lives in one adapter method. Future changes to compaction schema only touch the adapter.

3. **Privacy-tight:** Events carry only task IDs, timestamps, and aggregate metrics—no conversational content. Follows DESIGN.md §6 (aggregates up, details stay in subgraph).

4. **Linkage:** The `e` tag with `summary-of` marker creates a Nostr-native reference from the compaction back to the step's lifecycle event (42010), making the relationship traversable on the relay.

5. **Future-proof:** If the compaction machinery evolves (different compaction policies, summary techniques, etc.), the event-based approach extends cleanly with new tag fields without breaking existing queries.

**Next Steps for the Architect:**
1. Allocate a kind number in the 420xx block for compaction events (e.g., kind 42035: "Session Compaction").
2. Formalize the tag schema (branch, run, iter, step, compaction-session, compaction-span-start, compaction-span-end, e tag with summary-of marker).
3. Coordinate with Claude Code's harness to emit a transcript record type `"compaction"` when context is compacted, including the span and summary hash.
4. Update transcripts adapter to parse this record type and enrich with Fractal IDs via session lookup.

**Fallback (Candidate B)** if kind allocation is deferred: use status = "context-compacted" supplementary 42010 events, though this trades some clarity for re-use of an existing kind.

**Reject (Candidate C)** due to privacy and discovery constraints unless the repo is permanently private-in-subgraph.

---

## References

- DESIGN.md §5 (Evergreen Node), §6.1 (Privacy), §8 (Open Questions)
- `src/lindenmayer/bridge/adapters/transcripts.py` (current harvester, constraint source)
- `src/lindenmayer/bridge/adapters/sqlite.py` (Fractal identifiers: run_id, iter_id, step_id, session)
- `docs/kinds/42010-node-lifecycle.md`, `42020-run-accounting.md`, `42030-subgraph-digest.md` (existing tag schemas, range semantics)
- `docs/kinds/nip-oa-attestation.md` (NIP-OA reference, event reference patterns)
- Nostr specs: NIP-10 (event references), NIP-18 (quote reposts), NIP-51 (lists) — for marker idioms
- Fractal's per-tree SQLite DB schema (node, run, iter, step, event tables and columns)

