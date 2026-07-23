---
name: registry_state
title: Registry Node State
desc: Terminal state of the registry node -- deliverables shipped, test results, code locations.
tags: []
sources: []
created: 2026-07-23T20:37:35Z
updated: 2026-07-23T20:37:35Z
---

# Registry Node State

## Completion Status

**COMPLETED** — All 4 deliverables implemented and tested.

### Deliverables

1. ✅ Publisher (src/lindenmayer/registry/publisher.py)
   - Event generation for kinds 42050/38150
   - Deterministic ids from git commit data
   - Republish idempotency tests passing
   
2. ✅ Reader (src/lindenmayer/registry/reader.py)
   - Query relay, reconstruct version history
   - Signature verification via Event.verify()
   - Attestation validation via core.verify
   - Version ordering by version tag (not created_at)
   - Tampered-event rejection via RelayClient filtering
   
3. ✅ Linkage (src/lindenmayer/registry/linkage.py)
   - Parse template linkage lines (template: name vN @ sha)
   - Extract from NODE.md files (skips prose mentions of the format)
   - Validate against version events
   - Tested against the REAL tree/registry and tree/bridge contracts (pin 9f147a3)
   - READ-SIDE ONLY per condition 1
   
4. ✅ CLI (src/lindenmayer/registry/cli.py)
   - publish, list, show commands
   - Argparse-based (no click dependency)
   - Async relay operations

5. ✅ E2E Dogfood Test (tests/test_registry_e2e.py)
   - Register dev-node v1 @ 9f147a3 against mock relay
   - Read back history
   - Republish idempotency verification

### Test Results

- 243 total tests passing (all existing + 33 registry tests)
- Categories: publisher (9), reader (10), linkage (13, incl. real tree/ contracts), E2E (3)
- All acceptance criteria met

### Fixtures

- tests/fixtures/registry/dev-node/ created from tree/templates/dev-node/

### Architecture Notes

- Wire contracts: Documented in docs/kinds/ (42050, 38150)
- Deterministic ids: From git commit timestamps, not wall clock
- Version ordering: By semantic version string, not created_at
- Attestation: Optional via core's validate_attestation()
- Storage: Relay is the only storage (no new local databases)
- Linkage: Read-side validation only, no new event kinds

### Known Gaps for Future

- CLI auth-required relay support (NIP-42) — can add when needed
- Automatic relay queries for version lists in linkage validator
- Non-semantic version handling (currently lexical fallback)
- Cache/index for frequently-queried templates

### Code Locations

- Publisher: src/lindenmayer/registry/publisher.py
- Reader: src/lindenmayer/registry/reader.py
- Linkage: src/lindenmayer/registry/linkage.py
- CLI: src/lindenmayer/registry/cli.py
- Tests: tests/test_registry_*.py
- Wiki: wiki/registry_implementation.md
