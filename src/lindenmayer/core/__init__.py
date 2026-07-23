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
from lindenmayer.core.kinds import KIND_REGISTRY, KindModel, KindValidationError, parse_event
from lindenmayer.core.relay import (
    PrivateCapabilityError,
    RelayClient,
    RelayError,
    RelayRejection,
)
from lindenmayer.core.verify import (
    ApprovalCounts,
    AttestationLabel,
    AttestationOutcome,
    AttestationResult,
    AttestationState,
    attestation_state,
    count_approvals,
    filter_attested,
    is_approved,
    validate_attestation,
)

__all__ = [
    "CAP_PRIVATE_READ_GATING",
    "ApprovalCounts",
    "AttestationLabel",
    "AttestationOutcome",
    "AttestationResult",
    "AttestationState",
    "CapabilityAttestation",
    "ConfigError",
    "CoreConfig",
    "Event",
    "EventValidationError",
    "KIND_REGISTRY",
    "Keypair",
    "KindModel",
    "KindValidationError",
    "PrivateCapabilityError",
    "RelayClient",
    "RelayError",
    "RelayRejection",
    "attestation_state",
    "canonical_serialization",
    "compute_event_id",
    "count_approvals",
    "filter_attested",
    "is_approved",
    "parse_event",
    "schnorr_sign",
    "schnorr_verify",
    "validate_attestation",
]
