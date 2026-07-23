"""lindenmayer.core — the foundation library every other component consumes.

Module map (see README.md in this package for the full design posture):

- ``event``  — NIP-01 events: canonical id, signing, verification (trust root)
- ``keys``   — secp256k1 keypairs, BIP-340 Schnorr primitives
- ``kinds``  — typed models for Lindenmayer's custom event kinds
- ``relay``  — minimum-contract relay client (NIP-01 + NIP-29 + NIP-42)
- ``verify`` — the security boundary: attestation, approvals, revocation
- ``config`` — deployment configuration and capability attestations
"""

from lindenmayer.core.config import (
    CAP_PRIVATE_READ_GATING,
    CapabilityAttestation,
    ConfigError,
    CoreConfig,
)
from lindenmayer.core.event import (
    Event,
    EventValidationError,
    canonical_serialization,
    compute_event_id,
)
from lindenmayer.core.keys import Keypair, schnorr_sign, schnorr_verify

__all__ = [
    "CAP_PRIVATE_READ_GATING",
    "CapabilityAttestation",
    "ConfigError",
    "CoreConfig",
    "Event",
    "EventValidationError",
    "Keypair",
    "canonical_serialization",
    "compute_event_id",
    "schnorr_sign",
    "schnorr_verify",
]
