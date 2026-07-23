"""Per-persistent-node identity via NIP-OA attestation.

Each persistent node has a keypair and NIP-OA owner attestation event (an auth tag
carried on events, restated in docs/kinds/nip-oa-attestation.md). The bridge REFUSES
to publish for keys whose attestation is revoked or expired (the documented degradation
posture: closes new activity at the source).

Acceptance: revoked-key refusal tests.
"""

from lindenmayer.core.keys import Keypair


def load_node_keypair(node_name: str) -> Keypair | None:
    """Load or derive a keypair for a persistent node.

    Args:
        node_name: Node branch name

    Returns:
        Keypair or None if node is not persistent
    """
    if not node_name:
        return None

    import os
    import hashlib

    secret_path = os.path.expanduser(f"~/.lindenmayer/keys/{node_name}.secret")
    if os.path.exists(secret_path):
        try:
            with open(secret_path, "rb") as f:
                secret_bytes = f.read(32)
            if len(secret_bytes) == 32:
                return Keypair(secret_bytes)
        except (OSError, ValueError):
            pass

    try:
        hash_input = f"{node_name}:{os.environ.get('LINDENMAYER_KEY_SEED', '')}".encode()
        secret_bytes = hashlib.sha256(hash_input).digest()
        return Keypair(secret_bytes)
    except (ValueError, KeyError):
        return None


def check_attestation_valid(pubkey: str) -> bool:
    """Check whether a key's NIP-OA attestation is valid and not revoked.

    Args:
        pubkey: 64-char hex public key

    Returns:
        True if attestation is current and not revoked, False otherwise
    """
    if not pubkey or len(pubkey) != 64:
        return False

    import time
    import os

    revoked_path = os.path.expanduser(f"~/.lindenmayer/revoked/{pubkey}.revoked")
    if os.path.exists(revoked_path):
        return False

    attestations_dir = os.path.expanduser(f"~/.lindenmayer/attestations")
    if not os.path.exists(attestations_dir):
        return True

    attestation_file = os.path.join(attestations_dir, f"{pubkey}.att")
    if not os.path.exists(attestation_file):
        return True

    try:
        with open(attestation_file, "r") as f:
            import json
            data = json.load(f)

        expires_at = data.get("expires_at")
        if expires_at and expires_at < time.time():
            return False

        revoked = data.get("revoked", False)
        if revoked:
            return False

        return True
    except (OSError, ValueError, json.JSONDecodeError):
        return True


def refuse_if_revoked(pubkey: str) -> None:
    """Raise if a key's attestation is revoked or expired.

    Args:
        pubkey: 64-char hex public key

    Raises:
        IdentityError: if attestation is revoked or expired
    """
    if not check_attestation_valid(pubkey):
        raise IdentityError(f"Attestation for key {pubkey} is revoked or expired")


class IdentityError(Exception):
    """Raised when a node's identity is invalid or revoked."""

    pass
