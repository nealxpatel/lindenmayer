---
name: registry_implementation
title: Registry Implementation
desc: Template registry for publishing, reading, and validating template versions as Nostr events.
tags: []
sources: []
created: 2026-07-23T20:37:35Z
updated: 2026-07-23T20:37:35Z
---

# Registry Implementation

## Summary

Implemented the Lindenmayer template registry — a system for publishing, reading, and validating template versions as Nostr events. All four deliverables completed and tested.

## Deliverables

### 1. Publisher (`src/lindenmayer/registry/publisher.py`)

Reads a template directory, derives name/version/git_ref from content and commit pin, and emits 42050 + 38150 events.

**Features:**

- `extract_template_info()` — Parse template directory for name, version, git_ref
- `build_version_event()` — Create kind 42050 template-version event
- `build_pointer_event()` — Create kind 38150 template-pointer event
- Deterministic event ids from git commit timestamps (never wall clock)
- Republish idempotency: same input → identical event ids

**Tests:** 9 tests covering extraction, version/pointer event generation, idempotency

### 2. Reader (`src/lindenmayer/registry/reader.py`)

Query relay for 42050/38150 events by author and template name; reconstruct version history with verification.

**Features:**

- `get_version_history()` — Fetch and order versions by version tag (not created_at)
- `get_current_pointer()` — Fetch addressable pointer to current version
- Full NIP-01 signature verification via `Event.verify()`
- NIP-OA attestation validation via core's `validate_attestation()`
- Inheritance chain support via parent e-tag parsing
- Tampered-event rejection (RelayClient filters invalid signatures)

**Tests:** 10 tests covering version history, pointer lookup, inheritance, signature rejection

### 3. Linkage (`src/lindenmayer/registry/linkage.py`)

Parse and validate instance contract template linkage lines.

**Features:**

- `parse_template_linkage_line()` — Parse `template: <name> v<N> @ <sha>` format
- Handles markdown, backticks, extra whitespace variations
- `extract_from_node_md()` — Find linkage line in NODE.md file
- `validate_against_version()` — Verify linkage sha matches version event git_ref
- `resolve_linkage()` — Look up version event id from version list
- READ-SIDE ONLY: no new event kinds, no wire-visible artifacts

**Tests:** 13 tests covering parsing, extraction, validation, resolution, and the real tree/ contracts (bridge and registry both pin dev-node v1 @ 9f147a3)

### 4. CLI (`src/lindenmayer/registry/cli.py`)

Command-line interface for template operations.

**Commands:**

- `lindenmayer-registry publish <template_dir>` — Publish template version to relay
- `lindenmayer-registry list <author>` — List all templates from an author
- `lindenmayer-registry show <author> <name>` — Show version history for a template

**Features:**

- Uses stdlib argparse (no external deps like click)
- Async relay operations via core's RelayClient
- Generate or load keypairs for signing

### E2E Dogfood Test (`tests/test_registry_e2e.py`)

End-to-end integration test: register dev-node v1 @ 9f147a3 against mock relay and read back.

**Tests:** 3 tests covering single-version dogfood, republish idempotency, multi-version history

## Test Results

- **Total tests:** 243 passing
- **Registry-specific:** 33 tests across 4 test files
- **Test categories:**
  - Publisher goldens: 9 tests (idempotency assertion on event ids)
  - Reader round-trips: 10 tests (tampered-event rejection, inheritance)
  - Linkage validation: 13 tests (format variations, real tree/registry and tree/bridge contracts)
  - E2E dogfood: 3 tests (dev-node v1 registration and playback)

## Fixtures

- `tests/fixtures/registry/dev-node/` — Copy of tree/templates/dev-node/ for testing

## Architecture

### Wire Contracts

**Kind 42050 (Template Version) — Append-only:**
```json
{
  "kind": 42050,
  "tags": [
    ["template_name", "dev-node"],
    ["version", "1"],
    ["git_ref", "9f147a3"],
    ["e", "<parent_id>", "", "inherit"]  // optional parent
  ],
  "content": "{\"summary\": \"Initial release\"}"
}
```

**Kind 38150 (Template Pointer) — Addressable:**
```json
{
  "kind": 38150,
  "tags": [
    ["d", "dev-node"],
    ["e", "<version_event_id>"]
  ],
  "content": ""
}
```

### Key Design Decisions

1. **Deterministic ids from git commit data** — `created_at` comes from git author timestamp, not wall clock. Republishing produces identical event ids (bridge precedent, verdict 8266A685).

2. **Version ordering by tag, not created_at** — git timestamps are not guaranteed monotonic (condition 2, registry countersign). Sort by version string using semantic versioning rules.

3. **Attestation optional** — core's `validate_attestation()` returns ABSENT (not error) for unsigned events. Readers can accept both attested and unattested versions.

4. **No new storage** — registry relay IS the storage (§6.2 principle 2). No local index files, no database. MockRelay in tests demonstrates this.

5. **Linkage read-side only** — Instances link to templates but don't create new events. Validation terminates at 42050 version event id. Future evals can anchor to this id (§8 pillar, open design).

## Known Limitations

- CLI doesn't handle auth-required relays yet (relay's NIP-42 challenge/response). Can be added when needed.
- Version ordering assumes semantic versioning (1.0.0); non-semantic versions fall back to lexical sort.
- Linkage validation requires a version list; future work can query relay to build this automatically.

## References

- Wire contracts: `docs/kinds/42050-template-version.md`, `docs/kinds/38150-template-pointer.md`
- Platform design: `docs/DESIGN.md` §3 (templates), §6 (principles)
- Core API: `src/lindenmayer/core/` (event, relay, verify, keys)
- Bridge precedent: `src/lindenmayer/bridge/` (deterministic ids, idempotency tests)
