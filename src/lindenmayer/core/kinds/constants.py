"""Single-source kind numbers for Lindenmayer's custom event kinds.

These are unregistered proposals (see docs/research/relay-integration/
event-kinds.md, "Numbering caveat"): the architect may renumber, so every
other module — models, registry, tests, docs generators — must reference
these constants, never literals. This file is the one edit point.

Range semantics (NIP-01): the 420xx block is append-only regular history
(any kind >= 40000 defaults to regular on a compliant relay); the 381xx
block sits in the standard 30000–39999 addressable range so plain relays
collapse each (pubkey, kind, ``d``) stream to latest-only.
"""

from __future__ import annotations

# 420xx — append-only history (regular events)
KIND_NODE_LIFECYCLE = 42010
KIND_RUN_ACCOUNTING = 42020
KIND_SUBGRAPH_DIGEST = 42030
KIND_APPROVAL_REQUEST = 42040
KIND_APPROVAL_VERDICT = 42041
KIND_TEMPLATE_VERSION = 42050

# 381xx — addressable pointers (latest per pubkey+kind+d)
KIND_NODE_STATE_POINTER = 38110
KIND_TEMPLATE_POINTER = 38150

HISTORY_KINDS = frozenset(
    {
        KIND_NODE_LIFECYCLE,
        KIND_RUN_ACCOUNTING,
        KIND_SUBGRAPH_DIGEST,
        KIND_APPROVAL_REQUEST,
        KIND_APPROVAL_VERDICT,
        KIND_TEMPLATE_VERSION,
    }
)
ADDRESSABLE_KINDS = frozenset({KIND_NODE_STATE_POINTER, KIND_TEMPLATE_POINTER})
ALL_KINDS = HISTORY_KINDS | ADDRESSABLE_KINDS
