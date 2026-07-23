"""Deployment configuration: relay URL, key material, capability attestations.

No new storage systems (DESIGN.md §6.2): configuration is a TOML file read
with stdlib ``tomllib`` plus environment variables. Key material is never
stored in the config file itself — the file names *where* the key lives
(an env var or a file path), and ``load_keypair`` resolves it at runtime.

Capability attestations are the "verify, don't infer" mechanism from the
relay-integration research: relay-side behaviors that degrade silently on a
plain NIP-29 relay (private-group read gating above all) must be explicitly
attested by the deployment operator before the library will rely on them.
Absence of an attestation is a hard "no", not a "probably".
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from lindenmayer.core.keys import Keypair

__all__ = [
    "CAP_PRIVATE_READ_GATING",
    "CapabilityAttestation",
    "ConfigError",
    "CoreConfig",
]

# The one degradation that is not cosmetic (research aggregate, finding 4):
# relay-side enforcement of NIP-29 `private` read gating. Buzz satisfies it
# by construction; "NIP-29 compliant" alone does not.
CAP_PRIVATE_READ_GATING = "nip29-private-read-gating"


class ConfigError(ValueError):
    """Raised when configuration is missing, malformed, or unresolvable."""


class CapabilityAttestation(BaseModel):
    """An operator's explicit statement that this deployment's relay enforces
    a capability that the protocol alone does not guarantee.

    This is a config-level record of an operational fact, attributable to
    whoever operates the deployment — not a signed wire event. Consumers
    that need wire-level proof verify from the signed log (verify module).
    """

    capability: str
    attested_by: str = Field(description="operator identity: name or pubkey hex")
    attested_at: int = Field(description="unix timestamp of the attestation")
    note: str = ""

    @field_validator("capability", "attested_by")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must be non-empty")
        return value


class CoreConfig(BaseModel):
    """Top-level configuration for a Lindenmayer deployment."""

    relay_url: str
    capability_attestations: list[CapabilityAttestation] = Field(default_factory=list)
    secret_key_env: str = "LINDENMAYER_SECRET_KEY"
    secret_key_file: Path | None = None

    @field_validator("relay_url")
    @classmethod
    def _ws_url(cls, value: str) -> str:
        if not value.startswith(("ws://", "wss://")):
            raise ValueError("relay_url must be a ws:// or wss:// URL")
        return value

    # -- capabilities ------------------------------------------------------

    def has_capability(self, capability: str) -> bool:
        """True only if the deployment explicitly attests ``capability``."""
        return any(a.capability == capability for a in self.capability_attestations)

    def attestation_for(self, capability: str) -> CapabilityAttestation | None:
        for attestation in self.capability_attestations:
            if attestation.capability == capability:
                return attestation
        return None

    # -- key material ------------------------------------------------------

    def load_keypair(self) -> Keypair:
        """Resolve key material: env var first, then key file.

        The secret is 64-char hex. It never transits the config file; a
        world-readable key file is refused outright.
        """
        secret_hex = os.environ.get(self.secret_key_env, "").strip()
        if secret_hex:
            return self._keypair_from_hex(secret_hex, source=f"${self.secret_key_env}")
        if self.secret_key_file is not None:
            path = self.secret_key_file.expanduser()
            if not path.is_file():
                raise ConfigError(f"secret key file not found: {path}")
            mode = path.stat().st_mode & 0o777
            if mode & 0o077:
                raise ConfigError(
                    f"secret key file {path} is group/world-accessible "
                    f"(mode {mode:o}); chmod 600 it"
                )
            return self._keypair_from_hex(path.read_text().strip(), source=str(path))
        raise ConfigError(
            f"no key material: ${self.secret_key_env} is unset and no "
            "secret_key_file is configured"
        )

    @staticmethod
    def _keypair_from_hex(secret_hex: str, *, source: str) -> Keypair:
        try:
            return Keypair.from_hex(secret_hex)
        except ValueError as exc:
            # Deliberately excludes the material itself from the message.
            raise ConfigError(f"invalid secret key from {source}: {exc}") from exc

    # -- loading -----------------------------------------------------------

    @classmethod
    def from_toml(cls, path: str | Path) -> "CoreConfig":
        path = Path(path)
        try:
            data = tomllib.loads(path.read_text())
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise ConfigError(f"cannot read config {path}: {exc}") from exc
        try:
            return cls.model_validate(data)
        except ValueError as exc:
            raise ConfigError(f"invalid config {path}: {exc}") from exc
