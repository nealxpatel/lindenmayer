"""Per-persistent-node identity via NIP-OA attestation.

Each persistent node has a keypair and NIP-OA owner attestation event (an auth tag
carried on events, restated in docs/kinds/nip-oa-attestation.md). The bridge REFUSES
to publish for keys whose attestation is revoked or expired (the documented degradation
posture: closes new activity at the source).

Acceptance: revoked-key refusal tests.
"""

from lindenmayer.core.keys import KeyPair


def load_node_keypair(node_name: str) -> KeyPair | None:
    """Load or derive a keypair for a persistent node.

    Args:
        node_name: Node branch name

    Returns:
        KeyPair or None if node is not persistent
    """
    pass


def check_attestation_valid(pubkey: str) -> bool:
    """Check whether a key's NIP-OA attestation is valid and not revoked.

    Args:
        pubkey: 64-char hex public key

    Returns:
        True if attestation is current and not revoked, False otherwise
    """
    pass


def refuse_if_revoked(pubkey: str) -> None:
    """Raise if a key's attestation is revoked or expired.

    Args:
        pubkey: 64-char hex public key

    Raises:
        IdentityError: if attestation is revoked or expired
    """
    pass


class IdentityError(Exception):
    """Raised when a node's identity is invalid or revoked."""

    pass
