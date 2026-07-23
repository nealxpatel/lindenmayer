"""Publish translated events through core's relay client.

Stateless resume: the relay is the cursor — on startup, query own latest published
events per node and resume from there; no local state files, no new storage (§6.2).

Event ids MUST be deterministic: event content and created_at derive from Fractal
source rows (source timestamps, never wall clock), so a replay after cursor regression
reproduces identical ids.

Acceptance: idempotent-replay tests against a mock relay (restart mid-stream, no
duplicates, no gaps), asserting on event ids (architect condition 2, verdict 8266A685).
"""

from lindenmayer.core.relay import RelayClient
from lindenmayer.core.event import Event


class Publisher:
    """Stateless publisher that uses the relay as its cursor."""

    def __init__(self, relay_client: RelayClient):
        """Initialize with a relay client.

        Args:
            relay_client: Core relay client
        """
        pass

    def resume_from_relay(self, node: str) -> str | None:
        """Query relay for own latest published event and return its source timestamp.

        Args:
            node: Node name (branch)

        Returns:
            Source timestamp of latest event, or None if no prior events
        """
        pass

    def publish_event(self, event: Event) -> bool:
        """Publish an event to the relay.

        Args:
            event: Signed Event with deterministic id (derived from source timestamp)

        Returns:
            True if published successfully
        """
        pass

    def idempotent_replay(self, events: list[Event]) -> None:
        """Replay events idempotently: restart mid-stream reproduces identical ids."""
        pass
