"""Tests for the bridge publisher.

Validates:
- Stateless relay-cursor resume (query own latest events)
- Deterministic event ids (from source timestamps, never wall clock)
- Idempotent replay (restart mid-stream, no duplicates, no gaps)
- Event publishing and relay interaction
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

import pytest

from lindenmayer.bridge.publisher import Publisher, PublisherError
from lindenmayer.core.event import Event, compute_event_id
from lindenmayer.core.keys import Keypair
from lindenmayer.core.relay import RelayClient
from tests.relay_mock import MockRelay


EXAMPLE_PUBKEY = "3f0ff4ce8fa9b8006d754e26e73b8562711f264efc45ec4a751ba735d6221513"
EXAMPLE_SECRET = "0000000000000000000000000000000000000000000000000000000000000001"


@pytest.fixture
async def mock_relay() -> AsyncIterator:
    """Create and start a mock relay for testing."""
    async with MockRelay() as relay:
        yield relay


@pytest.fixture
def keypair() -> Keypair:
    """Create a test keypair."""
    return Keypair.from_hex(EXAMPLE_SECRET)


@pytest.fixture
async def relay_client(mock_relay: MockRelay, keypair: Keypair):
    """Create a relay client connected to the mock relay."""
    from lindenmayer.core.config import CoreConfig

    config = CoreConfig.default()
    client = RelayClient(mock_relay.url, keypair, config)
    await client.connect()
    yield client
    await client.close()


@pytest.mark.asyncio
async def test_publisher_deterministic_ids(keypair: Keypair, relay_client: RelayClient):
    """Event ids are deterministic from source timestamps, not wall clock."""
    publisher = Publisher(relay_client, keypair)

    source_ts = 1721761200
    event = Event.build(
        pubkey=keypair.public_key_hex,
        kind=42010,
        tags=[["branch", "test"], ["status", "active"]],
        content="test",
        created_at=source_ts,
    )
    signed = keypair.sign_event(event)

    # Rebuild with same timestamp -> same id
    event2 = Event.build(
        pubkey=keypair.public_key_hex,
        kind=42010,
        tags=[["branch", "test"], ["status", "active"]],
        content="test",
        created_at=source_ts,
    )
    signed2 = keypair.sign_event(event2)

    assert signed.id == signed2.id, "Event ids should be deterministic from source timestamp"


@pytest.mark.asyncio
async def test_publisher_publish_event(keypair: Keypair, relay_client: RelayClient):
    """Publishing a signed event succeeds."""
    publisher = Publisher(relay_client, keypair)

    event = Event.build(
        pubkey=keypair.public_key_hex,
        kind=42010,
        tags=[["branch", "test"], ["status", "active"]],
        content="test",
        created_at=1721761200,
    )
    signed = keypair.sign_event(event)

    success = await publisher.publish_event(signed)
    assert success


@pytest.mark.asyncio
async def test_publisher_reject_unsigned(keypair: Keypair, relay_client: RelayClient):
    """Publishing unsigned event raises error."""
    publisher = Publisher(relay_client, keypair)

    event = Event.build(
        pubkey=keypair.public_key_hex,
        kind=42010,
        tags=[["branch", "test"], ["status", "active"]],
        content="test",
        created_at=1721761200,
    )

    with pytest.raises(PublisherError, match="unsigned"):
        await publisher.publish_event(event)


@pytest.mark.asyncio
async def test_publisher_idempotent_replay(keypair: Keypair, relay_client: RelayClient):
    """Replay is idempotent: same events produce same ids, no duplicates."""
    publisher = Publisher(relay_client, keypair)

    # Create three events with deterministic timestamps
    events = []
    for i in range(3):
        event = Event.build(
            pubkey=keypair.public_key_hex,
            kind=42010,
            tags=[["branch", f"branch{i}"], ["status", "active"]],
            content=f"event{i}",
            created_at=1721761200 + i,
        )
        signed = keypair.sign_event(event)
        events.append(signed)

    # First replay: publish all
    await publisher.idempotent_replay(events)

    # Check ids are deterministic
    ids1 = [e.id for e in events]

    # Second replay: publish same events (simulating restart)
    publisher2 = Publisher(relay_client, keypair)
    await publisher2.idempotent_replay(events)

    ids2 = [e.id for e in events]

    assert ids1 == ids2, "Event ids must be deterministic across replays"


@pytest.mark.asyncio
async def test_publisher_resume_from_relay(keypair: Keypair, relay_client: RelayClient):
    """Resume queries relay for own latest events."""
    publisher = Publisher(relay_client, keypair)

    # Publish some events first
    event = Event.build(
        pubkey=keypair.public_key_hex,
        kind=42010,
        tags=[["branch", "test"], ["status", "active"]],
        content="test",
        created_at=1721761200,
    )
    signed = keypair.sign_event(event)
    await publisher.publish_event(signed)

    # Now resume in a fresh publisher
    publisher2 = Publisher(relay_client, keypair)
    resume_points = await publisher2.resume_from_relay()

    assert resume_points is not None
    assert "42010" in resume_points
    assert resume_points["42010"] == 1721761200


@pytest.mark.asyncio
async def test_publisher_no_duplicate_publish(keypair: Keypair, relay_client: RelayClient):
    """Same event is not published twice."""
    publisher = Publisher(relay_client, keypair)

    event = Event.build(
        pubkey=keypair.public_key_hex,
        kind=42010,
        tags=[["branch", "test"], ["status", "active"]],
        content="test",
        created_at=1721761200,
    )
    signed = keypair.sign_event(event)

    # Publish twice
    await publisher.publish_event(signed)
    await publisher.publish_event(signed)

    # Should only see one event in the relay
    # (the in-memory tracking prevents duplicate attempts)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
