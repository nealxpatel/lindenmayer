"""Test template publisher (kind 42050/38150 events and idempotency)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lindenmayer.core.keys import Keypair
from lindenmayer.registry.publisher import TemplateInfo, TemplatePublisher


@pytest.fixture
def keypair() -> Keypair:
    """Generate a test keypair."""
    return Keypair.generate()


@pytest.fixture
def repo_root() -> Path:
    """Get the repo root."""
    return Path(__file__).parent.parent.parent


@pytest.fixture
def publisher(repo_root: Path, keypair: Keypair) -> TemplatePublisher:
    """Create a publisher instance."""
    return TemplatePublisher(repo_root, keypair)


@pytest.fixture
def fixture_template_dir() -> Path:
    """Get the fixture template directory."""
    return Path(__file__).parent / "fixtures" / "registry" / "dev-node"


class TestExtractTemplateInfo:
    """Test template info extraction."""

    def test_extract_dev_node_template(self, publisher: TemplatePublisher, fixture_template_dir: Path):
        """Extract info from fixture dev-node template."""
        info = publisher.extract_template_info(fixture_template_dir)

        assert info.name == "dev-node"
        assert info.version == "1"
        assert len(info.git_ref) >= 7  # short sha
        assert info.created_at > 0

    def test_missing_readme_fails(self, publisher: TemplatePublisher, tmp_path: Path):
        """Extraction fails if README.md is missing."""
        template_dir = tmp_path / "no-readme"
        template_dir.mkdir()

        with pytest.raises(Exception, match="README.md not found"):
            publisher.extract_template_info(template_dir)


class TestVersionEvent:
    """Test kind 42050 version event generation."""

    def test_build_version_event(self, publisher: TemplatePublisher, keypair: Keypair):
        """Build a version event with correct structure."""
        info = TemplateInfo(
            name="test-template",
            version="1.0.0",
            git_ref="abc1234",
            created_at=1234567890,
        )

        event = publisher.build_version_event(info, summary="Test release")

        # Check structure
        assert event.kind == 42050
        assert event.pubkey == keypair.public_key_hex
        assert event.created_at == 1234567890

        # Check tags
        assert event.first_tag_value("template_name") == "test-template"
        assert event.first_tag_value("version") == "1.0.0"
        assert event.first_tag_value("git_ref") == "abc1234"

        # Check content
        content = json.loads(event.content)
        assert content["summary"] == "Test release"

        # Verify id computation is deterministic
        assert event.id_valid()

    def test_version_event_id_deterministic(self, publisher: TemplatePublisher, keypair: Keypair):
        """Version event ids are deterministic from content and created_at."""
        info = TemplateInfo(
            name="det-test",
            version="1.0.0",
            git_ref="abc1234",
            created_at=1234567890,
        )

        event1 = publisher.build_version_event(info, summary="Same")
        event2 = publisher.build_version_event(info, summary="Same")

        assert event1.id == event2.id


class TestPointerEvent:
    """Test kind 38150 pointer event generation."""

    def test_build_pointer_event(self, publisher: TemplatePublisher, keypair: Keypair):
        """Build a pointer event referencing a version."""
        info = TemplateInfo(
            name="test-template",
            version="1.0.0",
            git_ref="abc1234",
            created_at=1234567890,
        )
        version_event = publisher.build_version_event(info)

        pointer = publisher.build_pointer_event(version_event)

        # Check structure
        assert pointer.kind == 38150
        assert pointer.pubkey == keypair.public_key_hex
        assert pointer.content == ""

        # Check tags
        assert pointer.first_tag_value("d") == "test-template"
        assert pointer.first_tag_value("e") == version_event.id

        # Verify id computation
        assert pointer.id_valid()


class TestRepublishIdempotency:
    """Test that republishing produces identical event ids."""

    def test_republish_same_ids(self, publisher: TemplatePublisher, fixture_template_dir: Path):
        """Publishing the same template twice produces identical event ids."""
        info1 = publisher.extract_template_info(fixture_template_dir)
        info2 = publisher.extract_template_info(fixture_template_dir)

        event1 = publisher.build_version_event(info1)
        event2 = publisher.build_version_event(info2)

        # Ids should be identical since git commit data is deterministic
        assert event1.id == event2.id

    def test_pointer_republish_same_ids(self, publisher: TemplatePublisher, fixture_template_dir: Path):
        """Publishing the same pointer twice produces identical event ids."""
        info = publisher.extract_template_info(fixture_template_dir)

        version1 = publisher.build_version_event(info)
        version2 = publisher.build_version_event(info)

        pointer1 = publisher.build_pointer_event(version1)
        pointer2 = publisher.build_pointer_event(version2)

        assert pointer1.id == pointer2.id
