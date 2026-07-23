"""End-to-end dogfood test: register dev-node v1 and read back."""

from __future__ import annotations

from pathlib import Path

import pytest

from lindenmayer.core.config import CoreConfig
from lindenmayer.core.keys import Keypair
from lindenmayer.core.relay import RelayClient
from lindenmayer.registry.publisher import TemplatePublisher
from lindenmayer.registry.reader import TemplateReader
from relay_mock import MockRelay


@pytest.fixture
def repo_root() -> Path:
    """Get the repo root."""
    return Path(__file__).parent.parent.parent


@pytest.fixture
def fixture_template_dir() -> Path:
    """Get the fixture template directory (copy of dev-node)."""
    return Path(__file__).parent / "fixtures" / "registry" / "dev-node"


@pytest.mark.asyncio
async def test_e2e_dogfood_register_and_read(
    repo_root: Path, fixture_template_dir: Path
) -> None:
    """End-to-end: register dev-node v1 and read back history."""
    keypair = Keypair.generate()

    # Create mock relay
    async with MockRelay() as relay:
        config = CoreConfig(relay_url=relay.url)
        # Create publisher
        publisher = TemplatePublisher(repo_root, keypair)

        # Extract template info from fixture
        template_info = publisher.extract_template_info(fixture_template_dir)
        assert template_info.name == "dev-node"
        assert template_info.version == "1"

        # Build and sign events
        version_event = publisher.build_version_event(template_info)
        signed_version = keypair.sign_event(version_event)

        pointer_event = publisher.build_pointer_event(version_event)
        signed_pointer = keypair.sign_event(pointer_event)

        # Publish to mock relay (bypass client)
        relay.events.append(signed_version.to_dict())
        relay.events.append(signed_pointer.to_dict())

        # Create reader and read back
        async with RelayClient(relay.url, keypair, config) as client:
            reader = TemplateReader(client)

            # Read version history
            versions = await reader.get_version_history(keypair.public_key_hex, "dev-node")

            assert len(versions) == 1
            version = versions[0]
            assert version.name == "dev-node"
            assert version.version == "1"
            assert version.event_id == signed_version.id

            # Read current pointer
            current_id = await reader.get_current_pointer(keypair.public_key_hex, "dev-node")
            assert current_id == signed_version.id


@pytest.mark.asyncio
async def test_e2e_republish_idempotency(fixture_template_dir: Path) -> None:
    """Republishing the same template produces identical event ids."""
    keypair1 = Keypair.generate()

    repo_root = Path(__file__).parent.parent.parent

    # Publish with keypair1
    async with MockRelay() as relay:
        publisher1 = TemplatePublisher(repo_root, keypair1)
        info1 = publisher1.extract_template_info(fixture_template_dir)
        version1 = publisher1.build_version_event(info1)
        signed1 = keypair1.sign_event(version1)

        relay.events.append(signed1.to_dict())

        # Publish again with same keypair
        version1_again = publisher1.build_version_event(info1)
        signed1_again = keypair1.sign_event(version1_again)

        # Event ids must be identical
        assert signed1.id == signed1_again.id


@pytest.mark.asyncio
async def test_e2e_multiple_versions(repo_root: Path, fixture_template_dir: Path) -> None:
    """Test reading multiple versions of a template."""
    import json

    keypair = Keypair.generate()

    async with MockRelay() as relay:
        config = CoreConfig(relay_url=relay.url)
        from lindenmayer.core.event import Event

        # Create version 1 event manually
        v1_event = Event.build(
            pubkey=keypair.public_key_hex,
            kind=42050,
            tags=[
                ["template_name", "multi-test"],
                ["version", "1.0.0"],
                ["git_ref", "abc123"],
            ],
            content=json.dumps({"summary": "Initial release"}),
            created_at=1000000000,
        )
        signed_v1 = keypair.sign_event(v1_event)

        # Create version 2 event
        v2_event = Event.build(
            pubkey=keypair.public_key_hex,
            kind=42050,
            tags=[
                ["template_name", "multi-test"],
                ["version", "2.0.0"],
                ["git_ref", "def456"],
            ],
            content=json.dumps({"summary": "Add features"}),
            created_at=1000001000,
        )
        signed_v2 = keypair.sign_event(v2_event)

        # Publish both
        relay.events.append(signed_v1.to_dict())
        relay.events.append(signed_v2.to_dict())

        # Read history
        async with RelayClient(relay.url, keypair, config) as client:
            reader = TemplateReader(client)
            versions = await reader.get_version_history(keypair.public_key_hex, "multi-test")

            assert len(versions) == 2
            # Should be sorted by version, not created_at
            assert versions[0].version == "1.0.0"
            assert versions[1].version == "2.0.0"
            assert versions[0].summary == "Initial release"
            assert versions[1].summary == "Add features"
