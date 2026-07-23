"""Test instance template linkage validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from lindenmayer.registry.linkage import LinkageError, LinkageValidator, parse_template_linkage_line


class TestParseLinkageLine:
    """Test parsing template linkage lines."""

    def test_parse_standard_format(self):
        """Parse a standard linkage line."""
        line = "template: dev-node v1 @ 9f147a3"
        linkage = parse_template_linkage_line(line)

        assert linkage.name == "dev-node"
        assert linkage.version == "1"
        assert linkage.sha == "9f147a3"

    def test_parse_semantic_version(self):
        """Parse semantic version format."""
        line = "  **template:** `default-node v2.1.0 @ abc1234567`"
        linkage = parse_template_linkage_line(line)

        assert linkage.name == "default-node"
        assert linkage.version == "2.1.0"
        assert linkage.sha == "abc1234567"

    def test_parse_with_whitespace_variance(self):
        """Handle various whitespace patterns."""
        lines = [
            "template: test v1 @ abc1234",
            "template:test v1 @ abc1234",
            "template:  test  v1  @  abc1234",
        ]
        for line in lines:
            linkage = parse_template_linkage_line(line)
            assert linkage.name == "test"
            assert linkage.version == "1"
            assert linkage.sha == "abc1234"

    def test_parse_invalid_format_fails(self):
        """Invalid formats raise LinkageError."""
        invalid_lines = [
            "template: dev-node 1 @ 9f147a3",  # missing v
            "template: dev-node v1",  # missing @
            "no template line",
        ]
        for line in invalid_lines:
            with pytest.raises(LinkageError):
                parse_template_linkage_line(line)


class TestExtractFromNodeMd:
    """Test extracting linkage from NODE.md files."""

    def test_extract_from_fixture(self, tmp_path: Path):
        """Extract linkage from a NODE.md file."""
        # Create a test NODE.md with a template line
        node_file = tmp_path / "NODE.md"
        node_file.write_text(
            "# Test Node\n\n- **template:** `dev-node v1 @ 9f147a3`\n\n## Content\n"
        )
        validator = LinkageValidator()

        linkage = validator.extract_from_node_md(node_file)

        assert linkage.name == "dev-node"
        assert linkage.version == "1"
        assert linkage.sha == "9f147a3"

    def test_extract_missing_file_fails(self):
        """Raises LinkageError if file not found."""
        validator = LinkageValidator()

        with pytest.raises(LinkageError, match="cannot read"):
            validator.extract_from_node_md(Path("/nonexistent/NODE.md"))

    def test_extract_no_linkage_line_fails(self, tmp_path: Path):
        """Raises LinkageError if no linkage line found."""
        node_file = tmp_path / "NODE.md"
        node_file.write_text("# No template line here\nSome content.")

        validator = LinkageValidator()
        with pytest.raises(LinkageError, match="no template linkage line found"):
            validator.extract_from_node_md(node_file)


class TestRealTreeContracts:
    """Linkage validation against the real instance contracts in tree/.

    The charter's acceptance evidence: bridge and registry both carry the
    line `template: dev-node v1 @ 9f147a3` in their versioned contracts.
    """

    TREE = Path(__file__).parent.parent / "tree"

    @pytest.mark.parametrize("contract", ["registry", "bridge"])
    def test_extract_from_real_contract(self, contract: str):
        """Extract the real pin from each tree/ contract that carries it."""
        node_md = self.TREE / contract / "NODE.md"
        assert node_md.exists(), f"expected real contract at {node_md}"

        validator = LinkageValidator()
        linkage = validator.extract_from_node_md(node_md)

        assert linkage.name == "dev-node"
        assert linkage.version == "1"
        assert linkage.sha == "9f147a3"
        assert linkage.instance_path == node_md

    def test_registry_contract_prose_mention_skipped(self):
        """registry's NODE.md also quotes the linkage format in prose;
        extraction must land on the real pin line, not crash on the quote."""
        node_md = self.TREE / "registry" / "NODE.md"
        content = node_md.read_text()
        # Precondition: the prose mention exists (the format quote).
        assert "`template: <name> v<N> @ <sha>`" in content

        validator = LinkageValidator()
        linkage = validator.extract_from_node_md(node_md)
        assert linkage.sha == "9f147a3"

    def test_real_pin_resolves_against_registered_version(self):
        """The real contracts' pin resolves to a published dev-node version
        and validates against its git_ref — the instance → template-version
        association, terminating at the 42050 event id."""
        validator = LinkageValidator()
        linkage = validator.extract_from_node_md(self.TREE / "registry" / "NODE.md")

        versions = [
            {"name": "dev-node", "version": "1", "event_id": "a" * 64, "git_ref": "9f147a3"},
        ]
        event_id = validator.resolve_linkage(linkage, versions)
        assert event_id == "a" * 64

        assert validator.validate_against_version(linkage, event_id, "9f147a3") is True


class TestValidateAgainstVersion:
    """Test linkage validation against version event."""

    def test_valid_linkage(self):
        """Validate linkage matching version event."""
        from lindenmayer.registry.linkage import TemplateLinkage

        linkage = TemplateLinkage(name="test", version="1.0.0", sha="9f147a3")
        validator = LinkageValidator()

        # Should succeed with matching git_ref
        result = validator.validate_against_version(linkage, "event-id-1234", "9f147a3")
        assert result is True

    def test_full_sha_matches_short(self):
        """Full sha in version event matches short sha in linkage."""
        from lindenmayer.registry.linkage import TemplateLinkage

        linkage = TemplateLinkage(name="test", version="1.0.0", sha="9f147a3")
        validator = LinkageValidator()

        # Full sha starting with the short one should validate
        result = validator.validate_against_version(
            linkage, "event-id", "9f147a3a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d"
        )
        assert result is True

    def test_mismatched_sha_fails(self):
        """Mismatched shas raise LinkageError."""
        from lindenmayer.registry.linkage import TemplateLinkage

        linkage = TemplateLinkage(name="test", version="1.0.0", sha="9f147a3")
        validator = LinkageValidator()

        with pytest.raises(LinkageError, match="does not match"):
            validator.validate_against_version(linkage, "event-id", "abc1234")


class TestResolveLinkage:
    """Test resolving linkage to version event id."""

    def test_resolve_matching_version(self):
        """Resolve linkage to matching version event."""
        from lindenmayer.registry.linkage import TemplateLinkage

        linkage = TemplateLinkage(name="test", version="1.0.0", sha="abc123")
        versions = [
            {"name": "test", "version": "1.0.0", "event_id": "event-123"},
            {"name": "test", "version": "2.0.0", "event_id": "event-456"},
        ]

        validator = LinkageValidator()
        event_id = validator.resolve_linkage(linkage, versions)

        assert event_id == "event-123"

    def test_resolve_not_found(self):
        """Returns None if version not found."""
        from lindenmayer.registry.linkage import TemplateLinkage

        linkage = TemplateLinkage(name="test", version="3.0.0", sha="abc123")
        versions = [
            {"name": "test", "version": "1.0.0", "event_id": "event-123"},
        ]

        validator = LinkageValidator()
        event_id = validator.resolve_linkage(linkage, versions)

        assert event_id is None

    def test_resolve_ambiguous_fails(self):
        """Ambiguous resolution raises LinkageError."""
        from lindenmayer.registry.linkage import TemplateLinkage

        linkage = TemplateLinkage(name="test", version="1.0.0", sha="abc123")
        versions = [
            {"name": "test", "version": "1.0.0", "event_id": "event-123"},
            {"name": "test", "version": "1.0.0", "event_id": "event-456"},
        ]

        validator = LinkageValidator()
        with pytest.raises(LinkageError, match="ambiguous"):
            validator.resolve_linkage(linkage, versions)
