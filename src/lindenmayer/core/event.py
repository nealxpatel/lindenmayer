"""NIP-01 event model — the trust root of the platform.

Canonical id computation, signing, and verification for Nostr events.
Every other Lindenmayer component consumes events through this module;
nothing here knows about Lindenmayer kinds, relays, or Buzz.

Canonical serialization follows NIP-01: the id is the SHA-256 of the
UTF-8 JSON array ``[0, pubkey, created_at, kind, tags, content]`` with no
whitespace. Python's ``json.dumps(ensure_ascii=False, separators=(",", ":"))``
produces the same escaping as ``JSON.stringify`` (the de-facto reference
via nostr-tools), which is what published event ids are computed with.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Iterator

import lindenmayer.core.keys as _keys

__all__ = ["Event", "EventValidationError", "canonical_serialization", "compute_event_id"]


class EventValidationError(ValueError):
    """Raised when an event fails structural validation."""


def canonical_serialization(
    pubkey: str, created_at: int, kind: int, tags: list[list[str]], content: str
) -> bytes:
    """The NIP-01 canonical byte serialization whose SHA-256 is the event id."""
    return json.dumps(
        [0, pubkey, created_at, kind, tags, content],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def compute_event_id(
    pubkey: str, created_at: int, kind: int, tags: list[list[str]], content: str
) -> str:
    """Lowercase hex SHA-256 of the canonical serialization."""
    return hashlib.sha256(
        canonical_serialization(pubkey, created_at, kind, tags, content)
    ).hexdigest()


def _is_hex(value: str, length: int) -> bool:
    if len(value) != length or value != value.lower():
        return False
    try:
        bytes.fromhex(value)
    except ValueError:
        return False
    return True


@dataclass(frozen=True, slots=True)
class Event:
    """An immutable NIP-01 event.

    ``tags`` is stored as a tuple of tuples so instances are hashable; the
    wire form (``to_dict``/``to_json``) uses lists per NIP-01.
    """

    pubkey: str
    created_at: int
    kind: int
    tags: tuple[tuple[str, ...], ...]
    content: str
    id: str
    sig: str | None = field(default=None)

    # -- construction ------------------------------------------------------

    @classmethod
    def build(
        cls,
        *,
        pubkey: str,
        kind: int,
        tags: list[list[str]] | tuple[tuple[str, ...], ...] = (),
        content: str = "",
        created_at: int | None = None,
    ) -> "Event":
        """Build an unsigned event with a freshly computed id."""
        ts = int(time.time()) if created_at is None else int(created_at)
        tag_lists = [list(t) for t in tags]
        event_id = compute_event_id(pubkey, ts, kind, tag_lists, content)
        return cls(
            pubkey=pubkey,
            created_at=ts,
            kind=kind,
            tags=tuple(tuple(t) for t in tags),
            content=content,
            id=event_id,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Event":
        """Parse a wire-format event dict, validating structure (not signature)."""
        try:
            pubkey = data["pubkey"]
            created_at = data["created_at"]
            kind = data["kind"]
            tags = data["tags"]
            content = data["content"]
            event_id = data["id"]
        except (KeyError, TypeError) as exc:
            raise EventValidationError(f"missing event field: {exc}") from exc
        sig = data.get("sig")
        if not isinstance(pubkey, str) or not _is_hex(pubkey, 64):
            raise EventValidationError("pubkey must be 64-char lowercase hex")
        if not isinstance(event_id, str) or not _is_hex(event_id, 64):
            raise EventValidationError("id must be 64-char lowercase hex")
        if sig is not None and (not isinstance(sig, str) or not _is_hex(sig, 128)):
            raise EventValidationError("sig must be 128-char lowercase hex")
        if not isinstance(created_at, int) or isinstance(created_at, bool):
            raise EventValidationError("created_at must be an integer")
        if not isinstance(kind, int) or isinstance(kind, bool) or not 0 <= kind <= 65535:
            raise EventValidationError("kind must be an integer in [0, 65535]")
        if not isinstance(content, str):
            raise EventValidationError("content must be a string")
        if not isinstance(tags, list) or any(
            not isinstance(t, list) or any(not isinstance(v, str) for v in t) for t in tags
        ):
            raise EventValidationError("tags must be a list of lists of strings")
        return cls(
            pubkey=pubkey,
            created_at=created_at,
            kind=kind,
            tags=tuple(tuple(t) for t in tags),
            content=content,
            id=event_id,
            sig=sig,
        )

    @classmethod
    def from_json(cls, raw: str | bytes) -> "Event":
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise EventValidationError(f"invalid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise EventValidationError("event JSON must be an object")
        return cls.from_dict(data)

    # -- serialization -----------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "pubkey": self.pubkey,
            "created_at": self.created_at,
            "kind": self.kind,
            "tags": [list(t) for t in self.tags],
            "content": self.content,
        }
        if self.sig is not None:
            data["sig"] = self.sig
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, separators=(",", ":"))

    # -- integrity ---------------------------------------------------------

    def recompute_id(self) -> str:
        return compute_event_id(
            self.pubkey, self.created_at, self.kind, [list(t) for t in self.tags], self.content
        )

    def id_valid(self) -> bool:
        """Does the declared id match the canonical serialization?"""
        return self.id == self.recompute_id()

    def sig_valid(self) -> bool:
        """Is the signature a valid BIP-340 signature by ``pubkey`` over ``id``?

        False when unsigned. Does not check the id itself — use ``verify``.
        """
        if self.sig is None:
            return False
        return _keys.schnorr_verify(self.pubkey, bytes.fromhex(self.id), bytes.fromhex(self.sig))

    def verify(self) -> bool:
        """Full NIP-01 verification: id matches content AND signature is valid.

        This is the platform's trust root — every consumer that reads from a
        relay must call this (or a helper that does) before believing an event.
        """
        return self.id_valid() and self.sig_valid()

    # -- tag access --------------------------------------------------------

    def tag_values(self, name: str) -> Iterator[tuple[str, ...]]:
        """Yield the value portions (everything after the name) of matching tags."""
        for tag in self.tags:
            if tag and tag[0] == name:
                yield tag[1:]

    def first_tag_value(self, name: str) -> str | None:
        """The first value of the first tag named ``name``, or None."""
        for values in self.tag_values(name):
            return values[0] if values else None
        return None
