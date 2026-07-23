"""Shared machinery for kind models: tag/content parsing and event conversion.

Each kind model is a pydantic-v2 model whose fields cover both the
tag-borne and content-borne data of its wire shape. Conversion is
symmetric: ``to_event(pubkey=...)`` assembles an unsigned ``Event``;
``from_event(event)`` validates kind number, required tags, and content
JSON, raising ``KindValidationError`` with a message that names what was
wrong.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, ValidationError

from lindenmayer.core.event import Event

__all__ = ["KindModel", "KindValidationError"]


class KindValidationError(ValueError):
    """An event does not conform to the kind schema it was parsed as."""


def _is_hex(value: str, length: int) -> bool:
    if len(value) != length or value != value.lower():
        return False
    try:
        bytes.fromhex(value)
    except ValueError:
        return False
    return True


class KindModel(BaseModel):
    """Base for all Lindenmayer kind models."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    #: The kind number this model maps to (set per subclass from constants).
    KIND: ClassVar[int]

    # -- conversion (per-subclass shape) ----------------------------------

    def event_tags(self) -> list[list[str]]:
        """The tag list for the wire event (subclass responsibility)."""
        raise NotImplementedError

    def event_content(self) -> str:
        """The content string for the wire event (subclass responsibility)."""
        raise NotImplementedError

    @classmethod
    def _from_wire(cls, event: Event) -> dict[str, Any]:
        """Extract constructor kwargs from a wire event (subclass responsibility)."""
        raise NotImplementedError

    # -- public API --------------------------------------------------------

    def to_event(self, *, pubkey: str, created_at: int | None = None) -> Event:
        """Build the unsigned wire event for this model, authored by ``pubkey``."""
        return Event.build(
            pubkey=pubkey,
            kind=self.KIND,
            tags=self.event_tags(),
            content=self.event_content(),
            created_at=created_at,
        )

    @classmethod
    def from_event(cls, event: Event) -> "KindModel":
        """Parse a wire event into this model, validating shape and types."""
        if event.kind != cls.KIND:
            raise KindValidationError(
                f"{cls.__name__} expects kind {cls.KIND}, got kind {event.kind}"
            )
        kwargs = cls._from_wire(event)
        try:
            return cls(**kwargs)
        except ValidationError as exc:
            raise KindValidationError(
                f"kind {cls.KIND} ({cls.__name__}) invalid: {exc}"
            ) from exc

    # -- shared helpers ----------------------------------------------------

    @classmethod
    def _require_tag(cls, event: Event, name: str) -> str:
        value = event.first_tag_value(name)
        if value is None:
            raise KindValidationError(
                f"kind {cls.KIND} ({cls.__name__}) missing required tag '{name}'"
            )
        return value

    @classmethod
    def _content_object(cls, event: Event) -> dict[str, Any]:
        try:
            data = json.loads(event.content)
        except json.JSONDecodeError as exc:
            raise KindValidationError(
                f"kind {cls.KIND} ({cls.__name__}) content is not valid JSON: {exc}"
            ) from exc
        if not isinstance(data, dict):
            raise KindValidationError(
                f"kind {cls.KIND} ({cls.__name__}) content must be a JSON object"
            )
        return data

    @classmethod
    def _require_event_id(cls, value: str, what: str) -> str:
        if not _is_hex(value, 64):
            raise KindValidationError(
                f"kind {cls.KIND} ({cls.__name__}) {what} must be a 64-char "
                f"lowercase hex event id, got {value!r}"
            )
        return value

    @staticmethod
    def _dump_content(data: dict[str, Any]) -> str:
        return json.dumps(data, ensure_ascii=False, separators=(",", ":"))
