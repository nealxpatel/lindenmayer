"""Test template reader (query relay, version history, verification)."""

from __future__ import annotations

import json

import pytest

from lindenmayer.core.config import CoreConfig
from lindenmayer.core.event import Event
from lindenmayer.core.keys import Keypair
from lindenmayer.core.relay import RelayClient
from lindenmayer.registry.reader import ReaderError, TemplateReader
from relay_mock import MockRelay


@pytest.fixture
def keypair() -> Keypair:
    """Generate a test keypair."""
    return Keypair.generate()


class TestVersionHistoryReconstruction:
    """Test reconstructing version history from relay events."""

    @pytest.mark.asyncio
    async def test_read_single_version(self, keypair: Keypair):
        """Read a single template version from the relay."""
        # Create mock relay with a version event
        async with MockRelay() as relay:
            config = CoreConfig(relay_url=relay.url)
            # Build a version event
            event = Event.build(
                pubkey=keypair.public_key_hex,
                kind=42050,
                tags=[
                    ["template_name", "test"],
                    ["version", "1.0.0"],
                    ["git_ref", "abc1234"],
                ],
                content=json.dumps({"summary": "Initial release"}),
                created_at=1234567890,
            )
            signed = keypair.sign_event(event)

            # Add to relay events (mock relay holds them)
            relay.events.append(signed.to_dict())

            # Read back via client
            async with RelayClient(relay.url, keypair, config) as client:
                reader = TemplateReader(client)
                versions = await reader.get_version_history(keypair.public_key_hex, "test")

                assert len(versions) == 1
                assert versions[0].name == "test"
                assert versions[0].version == "1.0.0"
                assert versions[0].git_ref == "abc1234"
                assert versions[0].summary == "Initial release"

    @pytest.mark.asyncio
    async def test_version_history_sorted_by_version(self, keypair: Keypair):
        """Version history is sorted by version tag, not created_at."""
        async with MockRelay() as relay:
            config = CoreConfig(relay_url=relay.url)
            # Create versions with timestamps in reverse order (v3 earliest, v1 latest)
            for version, timestamp in [("3.0.0", 1000), ("1.0.0", 3000), ("2.0.0", 2000)]:
                event = Event.build(
                    pubkey=keypair.public_key_hex,
                    kind=42050,
                    tags=[
                        ["template_name", "test"],
                        ["version", version],
                    ],
                    content="{}",
                    created_at=timestamp,
                )
                signed = keypair.sign_event(event)
                relay.events.append(signed.to_dict())

            async with RelayClient(relay.url, keypair, config) as client:
                reader = TemplateReader(client)
                versions = await reader.get_version_history(keypair.public_key_hex, "test")

                # Should be sorted by version string (1.0.0, 2.0.0, 3.0.0)
                assert len(versions) == 3
                assert versions[0].version == "1.0.0"
                assert versions[1].version == "2.0.0"
                assert versions[2].version == "3.0.0"

    @pytest.mark.asyncio
    async def test_tampered_event_rejected(self, keypair: Keypair):
        """Events with invalid signatures are dropped (not delivered by client)."""
        async with MockRelay() as relay:
            config = CoreConfig(relay_url=relay.url)
            # Create a valid event
            event = Event.build(
                pubkey=keypair.public_key_hex,
                kind=42050,
                tags=[["template_name", "test"], ["version", "1.0.0"]],
                content="{}",
            )
            signed = keypair.sign_event(event)

            # Tamper with the content but keep the signature
            tampered_dict = signed.to_dict()
            tampered_dict["content"] = "tampered"
            relay.events.append(tampered_dict)

            # RelayClient.query() filters invalid events, so we get empty results
            async with RelayClient(relay.url, keypair, config) as client:
                reader = TemplateReader(client)
                versions = await reader.get_version_history(keypair.public_key_hex, "test")
                # Tampered event is dropped before it reaches the reader
                assert len(versions) == 0


class TestCurrentPointer:
    """Test reading the current version pointer."""

    @pytest.mark.asyncio
    async def test_get_current_pointer(self, keypair: Keypair):
        """Read the current template version pointer."""
        async with MockRelay() as relay:
            config = CoreConfig(relay_url=relay.url)
            # Create a version event
            version_event = Event.build(
                pubkey=keypair.public_key_hex,
                kind=42050,
                tags=[["template_name", "test"], ["version", "1.0.0"]],
                content="{}",
            )
            signed_version = keypair.sign_event(version_event)

            # Create a pointer event
            pointer_event = Event.build(
                pubkey=keypair.public_key_hex,
                kind=38150,
                tags=[["d", "test"], ["e", signed_version.id]],
                content="",
            )
            signed_pointer = keypair.sign_event(pointer_event)

            relay.events.append(signed_version.to_dict())
            relay.events.append(signed_pointer.to_dict())

            # Read pointer via client
            async with RelayClient(relay.url, keypair, config) as client:
                reader = TemplateReader(client)
                current_id = await reader.get_current_pointer(keypair.public_key_hex, "test")

                assert current_id == signed_version.id

    @pytest.mark.asyncio
    async def test_no_pointer_returns_none(self, keypair: Keypair):
        """Returns None if no pointer found."""
        async with MockRelay() as relay:
            config = CoreConfig(relay_url=relay.url)
            async with RelayClient(relay.url, keypair, config) as client:
                reader = TemplateReader(client)
                current_id = await reader.get_current_pointer(keypair.public_key_hex, "nonexistent")

                assert current_id is None


class TestInheritance:
    """Test template inheritance via parent e-tag."""

    @pytest.mark.asyncio
    async def test_parent_version_preserved(self, keypair: Keypair):
        """Parent version id is preserved when reading history."""
        async with MockRelay() as relay:
            config = CoreConfig(relay_url=relay.url)
            # Create parent version
            parent = Event.build(
                pubkey=keypair.public_key_hex,
                kind=42050,
                tags=[["template_name", "test"], ["version", "1.0.0"]],
                content="{}",
            )
            signed_parent = keypair.sign_event(parent)

            # Create child version with parent reference
            child = Event.build(
                pubkey=keypair.public_key_hex,
                kind=42050,
                tags=[
                    ["template_name", "test"],
                    ["version", "2.0.0"],
                    ["e", signed_parent.id, "", "inherit"],
                ],
                content="{}",
            )
            signed_child = keypair.sign_event(child)

            relay.events.append(signed_parent.to_dict())
            relay.events.append(signed_child.to_dict())

            async with RelayClient(relay.url, keypair, config) as client:
                reader = TemplateReader(client)
                versions = await reader.get_version_history(keypair.public_key_hex, "test")

                # Check parent reference on child
                child_version = next((v for v in versions if v.version == "2.0.0"), None)
                assert child_version is not None
                assert child_version.parent_version_id == signed_parent.id
