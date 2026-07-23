"""secp256k1 key handling: BIP-340 Schnorr signing and verification.

Thin wrapper over coincurve (libsecp256k1 — the BIP-340 reference C
implementation). This module is the only place in Lindenmayer that touches
raw key material; everything else works with hex pubkeys and `Event`s.

Key-material discipline: secrets live in memory as bytes, are never logged,
and never appear in repr/str output.
"""

from __future__ import annotations

from coincurve.keys import PrivateKey, PublicKeyXOnly

__all__ = ["Keypair", "schnorr_sign", "schnorr_verify"]


def schnorr_verify(pubkey_hex: str, message: bytes, signature: bytes) -> bool:
    """Verify a BIP-340 Schnorr signature by an x-only pubkey over ``message``.

    Returns False (never raises) on malformed keys or signatures — callers
    treat verification failure uniformly regardless of why the input is bad.
    """
    try:
        pubkey = PublicKeyXOnly(bytes.fromhex(pubkey_hex))
        return pubkey.verify(signature, message)
    except Exception:
        return False


def schnorr_sign(secret: bytes, message: bytes, aux_rand: bytes | None = None) -> bytes:
    """Produce a BIP-340 Schnorr signature over ``message``.

    ``aux_rand`` is the 32-byte auxiliary randomness from BIP-340; None lets
    the backend choose (test vectors pass it explicitly).
    """
    key = PrivateKey(secret)
    if aux_rand is None:
        return key.sign_schnorr(message)
    return key.sign_schnorr(message, aux_randomness=aux_rand)


class Keypair:
    """A secp256k1 keypair identified by its x-only public key (hex)."""

    __slots__ = ("_private",)

    def __init__(self, secret: bytes) -> None:
        if len(secret) != 32:
            raise ValueError("secret key must be exactly 32 bytes")
        self._private = PrivateKey(secret)

    @classmethod
    def generate(cls) -> "Keypair":
        return cls(PrivateKey().secret)

    @classmethod
    def from_hex(cls, secret_hex: str) -> "Keypair":
        return cls(bytes.fromhex(secret_hex))

    @property
    def public_key_hex(self) -> str:
        """The 64-char lowercase hex x-only public key (the Nostr pubkey)."""
        return self._private.public_key_xonly.format().hex()

    def sign(self, message: bytes, aux_rand: bytes | None = None) -> bytes:
        if aux_rand is None:
            return self._private.sign_schnorr(message)
        return self._private.sign_schnorr(message, aux_randomness=aux_rand)

    def sign_event(self, event):  # noqa: ANN001, ANN201 — Event typed at call sites; avoids import cycle
        """Return a signed copy of ``event`` authored by this keypair.

        The event's pubkey must already be this keypair's pubkey (the id
        commits to the pubkey, so signing someone else's event body would
        just produce an invalid event).
        """
        from dataclasses import replace

        if event.pubkey != self.public_key_hex:
            raise ValueError("event.pubkey does not match this keypair")
        if not event.id_valid():
            raise ValueError("event id does not match its canonical serialization")
        signature = self.sign(bytes.fromhex(event.id))
        return replace(event, sig=signature.hex())

    def __repr__(self) -> str:  # never leak the secret
        return f"Keypair(pubkey={self.public_key_hex})"
