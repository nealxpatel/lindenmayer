"""Read template versions from a relay.

Query a relay for 42050/38150 events by author and template name, reconstruct
the full version history, and verify signatures and author attestation via
core's verification module. Version history is ordered by the `version` tag
(treating `created_at` as informational — git commit timestamps are not
guaranteed monotonic per condition 2, registry countersign).
"""

from __future__ import annotations

from dataclasses import dataclass

from lindenmayer.core.event import Event
from lindenmayer.core.verify import AttestationOutcome, validate_attestation

__all__ = ["TemplateReader", "TemplateVersion", "ReaderError"]


class ReaderError(Exception):
    """Template reader operation failed."""

    pass


@dataclass
class TemplateVersion:
    """A single template version from the relay."""

    name: str
    version: str
    git_ref: str
    created_at: int
    summary: str
    event_id: str
    parent_version_id: str | None = None


class TemplateReader:
    """Read and validate template versions from a relay."""

    def __init__(self, relay_client) -> None:
        """Initialize reader with a relay client.

        Args:
            relay_client: Core RelayClient instance
        """
        self._relay = relay_client

    async def get_version_history(self, author: str, template_name: str) -> list[TemplateVersion]:
        """Fetch and reconstruct full version history for a template.

        Queries the relay for all kind 42050 events by author with matching
        template_name tag, verifies signatures and attestation, and returns
        them sorted by version (created_at is informational only).

        Args:
            author: Pubkey of the template author
            template_name: Name of the template

        Returns:
            List of TemplateVersion objects sorted by version (stable order)

        Raises:
            ReaderError: If query fails or events fail verification
        """
        try:
            filters = [
                {
                    "kinds": [42050],
                    "authors": [author],
                    "#template_name": [template_name],
                }
            ]
            events = await self._relay.query(filters)
        except Exception as e:
            raise ReaderError(f"relay query failed: {e}") from e

        versions: list[TemplateVersion] = []
        for event in events:
            # Verify event integrity
            if not event.verify():
                raise ReaderError(f"event {event.id} failed NIP-01 verification")

            # Verify author attestation (if present)
            result = validate_attestation(event)
            if result.outcome == AttestationOutcome.INVALID:
                raise ReaderError(f"event {event.id} has invalid attestation: {result.reason}")

            # Extract version metadata
            version_name = event.first_tag_value("template_name")
            version_str = event.first_tag_value("version")
            git_ref = event.first_tag_value("git_ref")

            if not version_name or not version_str:
                raise ReaderError(f"event {event.id} missing template_name or version tag")

            # Parse content
            import json

            try:
                content = json.loads(event.content)
                summary = content.get("summary", "")
            except (json.JSONDecodeError, TypeError):
                summary = ""

            # Check for parent version (inheritance)
            # Tag format: ["e", "<id>", "", "inherit"]
            # tag_values("e") yields ("<id>", "", "inherit")
            parent_id = None
            for tag_vals in event.tag_values("e"):
                if len(tag_vals) >= 3 and tag_vals[2] == "inherit":
                    parent_id = tag_vals[0]
                    break

            versions.append(
                TemplateVersion(
                    name=version_name,
                    version=version_str,
                    git_ref=git_ref or "",
                    created_at=event.created_at,
                    summary=summary,
                    event_id=event.id,
                    parent_version_id=parent_id,
                )
            )

        # Sort by version string (stable ordering, not wall-clock time)
        # Use natural version comparison if versions are semantic, else lexical
        versions.sort(key=lambda v: _version_sort_key(v.version))
        return versions

    async def get_current_pointer(self, author: str, template_name: str) -> str | None:
        """Get the current template version from the addressable pointer.

        Queries kind 38150 (Template Pointer) by author and d-tag for the
        template name, returns the current version event id if found.

        Args:
            author: Pubkey of the template author
            template_name: Name of the template

        Returns:
            Event id of the current version, or None if no pointer found

        Raises:
            ReaderError: If query fails or pointer is invalid
        """
        try:
            filters = [
                {
                    "kinds": [38150],
                    "authors": [author],
                    "#d": [template_name],
                }
            ]
            events = await self._relay.query(filters)
        except Exception as e:
            raise ReaderError(f"relay query failed: {e}") from e

        if not events:
            return None

        # Most recent addressable event wins (relays collapse these)
        latest = max(events, key=lambda e: (e.created_at, e.id))

        if not latest.verify():
            raise ReaderError(f"pointer event {latest.id} failed NIP-01 verification")

        version_id = latest.first_tag_value("e")
        if not version_id:
            raise ReaderError(f"pointer event {latest.id} missing e tag")

        return version_id


def _version_sort_key(version: str) -> tuple:
    """Convert semantic version string to a sortable tuple.

    Handles both semantic versioning (1.2.3) and single numbers (1).
    Falls back to lexical sort on parse failure.
    """
    try:
        parts = version.split(".")
        return tuple(int(p) for p in parts)
    except (ValueError, AttributeError):
        # Fallback to lexical sort if not semantic
        return (version,)
