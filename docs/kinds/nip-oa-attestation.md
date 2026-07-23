# NIP-OA: Owner Attestation

## Overview

**Status:** Draft (external, from block/buzz)  
**Note:** This document is a **restatement** of the upstream NIP-OA draft (pinned to buzz commit 06e3d82) for historical preservation. NIP-OA is an `auth` TAG, not an event kind. Lindenmayer uses NIP-OA as-is; this document does not modify the specification, only restates it so future draft revisions do not silently invalidate historical attestation events' meaning.

**Purpose:** NIP-OA provides a way for an agent (identified by a Nostr pubkey) to attest that it is authorized to act on behalf of an owner, with conditions on what the agent is authorized to do.

## Tag Format

The NIP-OA `auth` tag is a **4-element tag** attached to any event:

```
["auth", "<owner-pubkey-hex>", "<conditions>", "<signature-hex>"]
```

- **Element 0:** Literal string `"auth"`
- **Element 1:** Owner's 64-char lowercase hex pubkey
- **Element 2:** Conditions string (see Conditions Grammar below)
- **Element 3:** 128-char lowercase hex BIP-340 signature

## Signature Preimage and Verification

The signature is computed over a **canonical preimage string**:

```
nostr:agent-auth:<agent-pubkey>:<conditions>
```

Where:
- `<agent-pubkey>` is the signing agent's 64-char lowercase hex pubkey
- `<conditions>` is the exact conditions string (no whitespace normalization)

The preimage is UTF-8 encoded and hashed with SHA-256 (per NIP-01 canonical hashing), then signed per BIP-340 (Schnorr signature) with the owner's private key.

Verification:
1. Extract the `auth` tag from the event
2. Reconstruct the preimage: `"nostr:agent-auth:" + agent_pubkey + ":" + conditions`
3. Compute SHA-256 of the preimage bytes
4. Verify the BIP-340 signature using the owner's (element 1) pubkey

## Conditions Grammar

Conditions are a string describing what the agent is authorized to do, joined by `&` with no whitespace:

```
<condition>&<condition>&...
```

Each condition has one of these forms:

| Form | Meaning |
|------|---------|
| `kind=<decimal>` | Agent may create events of exactly this kind number. Decimal, no leading zeros. |
| `created_at<{timestamp}` | Agent may create events with `created_at` strictly less than this Unix timestamp. |
| `created_at>{timestamp}` | Agent may create events with `created_at` strictly greater than this Unix timestamp. |

**Constraints:**
- No whitespace anywhere in the conditions string
- Decimal kind numbers must be canonical (no leading zeros)
- Timestamps are decimal Unix epoch seconds
- No self-attestation: the agent's key cannot appear in the owner field (an agent cannot vouch for itself)
- Exactly one `auth` tag per event (multiple attestations not supported)

**Example:**
```
kind=42010&created_at>1721761200&created_at<1721764800
```

Means: agent may create kind 42010 events with timestamps between 2026-07-24T00:00:00Z and 2026-07-24T01:00:00Z (Unix epoch 1721761200–1721764800).

## Worked Example: Attestation Tag

An owner (pubkey `3f0ff4ce...`) attests that an agent (pubkey `abc123de...`) may create kind 42010 events between timestamps 1721761200 and 1721764800:

```
[
  "auth",
  "3f0ff4ce8fa9b8006d754e26e73b8562711f264efc45ec4a751ba735d6221513",
  "kind=42010&created_at>1721761200&created_at<1721764800",
  "9f8e7d6c5b4a39281716151413121110090807060504030201000000000000000" 
]
```

The signature `9f8e7d...` is computed over the preimage:
```
nostr:agent-auth:abc123de...:kind=42010&created_at>1721761200&created_at<1721764800
```

## Worked Example: Full Event with Attestation

An agent creates a kind 42010 event and includes an owner attestation:

```json
{
  "kind": 42010,
  "tags": [
    ["branch", "main.core.kinds"],
    ["status", "active"],
    ["run", "run-001"],
    ["auth", "3f0ff4ce8fa9b8006d754e26e73b8562711f264efc45ec4a751ba735d6221513", "kind=42010&created_at>1721761200&created_at<1721764800", "9f8e7d6c5b4a39281716151413121110090807060504030201000000000000000"]
  ],
  "content": "{\"reason\":\"Initial startup\"}",
  "created_at": 1721761200,
  "pubkey": "abc123def0123456789abcdef0123456789abcdef0123456789abcdef0123456",
  "id": "abc123def0123456789abcdef0123456789abcdef0123456789abcdef0123456",
  "sig": null
}
```

The agent's pubkey is `abc123de...` (appears in the event's `pubkey` field). The owner's pubkey is in the `auth` tag. The event's `created_at` is within the attestation's time window.

## Integration with Lindenmayer

Lindenmayer uses NIP-OA to enable **persistent node delegation**: a parent node (the owner) attests that a child node (the agent, identified by its Nostr pubkey) is authorized to emit certain event kinds within certain time windows.

This provides:
- **Verifiable lineage:** any third party can verify the attestation chain
- **Delegation:** a parent can authorize child nodes without sharing its private key
- **Scope limitation:** attestations bind agents to specific kinds and time windows, preventing overreach
- **Immutability:** attestations are never revoked; a new attestation can revoke a prior one by including newer conditions

## Relationship to Event Kinds

Per event-kinds.md §1.7, Lindenmayer does not mint its own kind for attestation — it uses NIP-OA's tag directly, because the draft's event *shape* (or in this case, tag shape) is exactly what's needed and re-deriving an equivalent would just be NIP-OA with extra steps.

The attestation is **not** an event kind; it's a tag attached to events. Any event (kind 42010, 42020, or any other) can carry an `auth` tag to indicate the agent's authorization.

## Upstream Dependency Note

This restatement was compiled from NIP-OA.md in block/buzz commit 06e3d82. If the upstream draft evolves, new attestations should follow the upstream version, but this document preserves the semantics of historical attestation events as they were understood at write-time. A reader verifying an old attestation can consult this document to understand what the author intended, even if the upstream draft has since changed.
