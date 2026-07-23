# Kind 38150: Template Pointer

## Overview

**Kind Number:** 38150  
**Range:** Addressable (latest per pubkey+kind+d)  
**Status:** Draft  

Addressable pointer to the current/default version of a template. Resolves "what's the current version of template X" in one query instead of walking the full version history. Pure indirection: content is empty or `{}`.

## Range Semantics

This kind is in the **381xx** block (30000–39999), which per NIP-01 is **addressable** / parameterized-replaceable: a plain relay automatically collapses each (pubkey, kind, `d`-tag) stream to keep only the latest pointer event. This is the correct semantics for "what is current" — you want O(1) lookups without replaying history.

Contrast with kind 42050 (Template Version), which uses the 420xx regular range to preserve the full version history.

## Tag Table

| Tag | Meaning | Required? | Format |
|-----|---------|-----------|--------|
| `d` | Template name (the addressable key) | yes | string |
| `e` | The current/default Template Version event id | yes | 64-char lowercase hex |

## Content JSON Schema

```
(empty string or "{}")
```

Content for this kind is empty or `{}`. No other content is valid. This kind is pure indirection, not a data container.

## Worked Example

```json
{
  "kind": 38150,
  "tags": [
    ["d", "default-node"],
    ["e", "7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f"]
  ],
  "content": "",
  "created_at": 1721761207,
  "pubkey": "3f0ff4ce8fa9b8006d754e26e73b8562711f264efc45ec4a751ba735d6221513",
  "id": "9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f9b0c",
  "sig": null
}
```

## Invariant

This pointer is a convenience index over the version history, not a second source of truth. Losing this pointer (e.g., on a relay that doesn't support addressable collapse) degrades to "replay kind 42050 history to find the latest version," never data loss.

When updated (a new version is released), this event is replaced atomically by the relay (addressable semantics): clients see the old pointer until the new one is published, then instantly see the new one. No race conditions between pointer and version events.
