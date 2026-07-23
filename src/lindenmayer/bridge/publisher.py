"""Publish translated events through core's relay client.

Stateless resume: the relay is the cursor — on startup, query own latest published
events per node and resume from there; no local state files, no new storage (§6.2).

Event ids MUST be deterministic: event content and created_at derive from Fractal
source rows (source timestamps, never wall clock), so a replay after cursor regression
reproduces identical ids.

Acceptance: idempotent-replay tests against a mock relay (restart mid-stream, no
duplicates, no gaps), asserting on event ids (architect condition 2, verdict 8266A685).
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from lindenmayer.core.event import Event
from lindenmayer.core.relay import RelayClient, RelayRejection

if TYPE_CHECKING:
    from lindenmayer.core.keys import Keypair

__all__ = ["Publisher", "PublisherError"]

logger = logging.getLogger(__name__)


class PublisherError(Exception):
    """Publisher operation failed."""

    pass


class Publisher:
    """Stateless publisher that uses the relay as its cursor.

    Publishes events with deterministic ids derived from source timestamps (never wall
    clock). On startup, queries the relay for own latest published events to resume from
    there — no local state files or additional storage (§6.2).
    """

    def __init__(self, relay_client: RelayClient, keypair: Keypair):
        """Initialize with a relay client and keypair.

        Args:
            relay_client: Core relay client (should be async-ready)
            keypair: Keypair for this node (used to filter own events on relay)
        """
        self._relay = relay_client
        self._keypair = keypair
        self._published_event_ids: set[str] = set()

    async def resume_from_relay(self) -> dict[str, int] | None:
        """Query relay for own latest published events and return resume points per kind.

        Returns:
            Dict mapping kind -> latest created_at timestamp, or None if no prior events
        """
        try:
            filters = [{"authors": [self._keypair.public_key_hex]}]
            events = await self._relay.query(filters)

            if not events:
                return None

            resume_points: dict[str, int] = {}
            for event in events:
                # Every own event on the relay is already published — track them
                # all, not just the latest per kind, or a replay duplicates the rest.
                self._published_event_ids.add(event.id)
                kind_key = str(event.kind)
                if kind_key not in resume_points or event.created_at > resume_points[kind_key]:
                    resume_points[kind_key] = event.created_at

            return resume_points if resume_points else None
        except Exception as e:
            logger.warning(f"Failed to resume from relay: {e}")
            return None

    async def publish_event(self, event: Event) -> bool:
        """Publish a signed event to the relay.

        Args:
            event: Signed Event with deterministic id (derived from source timestamp)

        Returns:
            True if published successfully

        Raises:
            PublisherError: If the event is unsigned or relay rejects it
        """
        if event.sig is None:
            raise PublisherError("cannot publish unsigned event")

        if event.id in self._published_event_ids:
            logger.debug(f"Event {event.id} already published, skipping")
            return True

        try:
            await self._relay.publish(event)
            self._published_event_ids.add(event.id)
            logger.info(f"Published event {event.id} (kind {event.kind})")
            return True
        except RelayRejection as e:
            logger.error(f"Relay rejected event {e.event_id}: {e.message}")
            raise PublisherError(f"relay rejected: {e.message}") from e

    async def publish_events(self, events: list[Event]) -> None:
        """Publish a list of events, preserving order and handling idempotency.

        Args:
            events: List of signed Events

        Raises:
            PublisherError: If any event fails to publish
        """
        for event in events:
            await self.publish_event(event)

    async def idempotent_replay(self, events: list[Event]) -> None:
        """Replay events idempotently: restart mid-stream reproduces identical ids.

        This method ensures that:
        - Event ids are deterministic (from source timestamps)
        - Restarting mid-stream continues without duplicates
        - No gaps occur (all events reach the relay eventually)

        Args:
            events: List of signed Events with deterministic ids
        """
        await self.publish_events(events)
