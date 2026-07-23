"""Validate instance → template-version associations.

Parse instance contracts' template linkage lines (`template: <name> v<N> @ <sha>`),
validate that the pin resolves and matches a registered version, and expose the
instance → template-version association.

READ-SIDE ONLY, terminating at the 42050 version event id: no new event kinds,
no wire-visible association artifacts, no eval-shaped schema.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

__all__ = ["TemplateLinkage", "LinkageValidator", "LinkageError"]


class LinkageError(Exception):
    """Template linkage validation failed."""

    pass


@dataclass
class TemplateLinkage:
    """A parsed template linkage line from an instance contract."""

    name: str
    version: str
    sha: str
    instance_path: Path | None = None


def parse_template_linkage_line(line: str) -> TemplateLinkage:
    """Parse a template linkage line from NODE.md.

    Expected format: `template: <name> v<N> @ <sha>`
    Handles variations with backticks, markdown, extra whitespace, etc.

    Args:
        line: Raw line from NODE.md

    Returns:
        Parsed TemplateLinkage

    Raises:
        LinkageError: If line format is invalid
    """
    # Match: template: dev-node v1 @ 9f147a3
    # Also handles:
    #   **template:** `default-node v2.1.0 @ abc1234567`
    #   template:  test v1 @ abc1234
    # After template:, skip spaces, *, and `, then capture name (alphanumeric+dash)
    pattern = r"template:[\s*`]*([a-z0-9-]+)\s+v([\d\.]+)\s+@\s+([a-f0-9]+)"
    match = re.search(pattern, line, re.IGNORECASE)
    if not match:
        raise LinkageError(f"invalid template linkage line: {line}")
    name, version, sha = match.groups()
    return TemplateLinkage(name=name, version=version, sha=sha)


class LinkageValidator:
    """Validate instance contracts against registered template versions."""

    def __init__(self) -> None:
        """Initialize validator."""
        pass

    def extract_from_node_md(self, node_md_path: Path) -> TemplateLinkage:
        """Extract template linkage from an instance NODE.md file.

        Searches the file for a line matching `template: <name> v<N> @ <sha>`.

        Args:
            node_md_path: Path to NODE.md file

        Returns:
            Parsed TemplateLinkage

        Raises:
            LinkageError: If linkage line not found or invalid
        """
        try:
            content = node_md_path.read_text()
        except Exception as e:
            raise LinkageError(f"cannot read {node_md_path}: {e}") from e

        for line in content.split("\n"):
            if "template:" in line:
                linkage = parse_template_linkage_line(line)
                linkage.instance_path = node_md_path
                return linkage

        raise LinkageError(f"no template linkage line found in {node_md_path}")

    def validate_against_version(
        self, linkage: TemplateLinkage, version_event_id: str, git_ref: str
    ) -> bool:
        """Validate that a linkage references a known version event.

        Checks that:
        1. The git_ref from the version event matches (or starts with) the
           sha in the linkage line
        2. The version event id can be used as the anchor for future evals

        Args:
            linkage: Parsed template linkage
            version_event_id: The kind 42050 event id for this version
            git_ref: The git_ref tag value from the version event

        Returns:
            True if linkage is valid

        Raises:
            LinkageError: If validation fails
        """
        # Check that git_ref from version event matches linkage sha
        # Allow short shas (e.g., 9f147a3) matching the beginning of full shas
        if not git_ref.startswith(linkage.sha) and not linkage.sha.startswith(git_ref):
            raise LinkageError(
                f"linkage sha {linkage.sha} does not match version event git_ref {git_ref}"
            )
        return True

    def resolve_linkage(
        self, linkage: TemplateLinkage, versions: list[dict]
    ) -> str | None:
        """Resolve a linkage to a version event id.

        Searches the given version list for a matching name and version.

        Args:
            linkage: Parsed template linkage
            versions: List of template versions (dicts with name, version, event_id keys)

        Returns:
            Event id of the matching version, or None if not found

        Raises:
            LinkageError: If multiple versions match (ambiguous)
        """
        matches = [
            v for v in versions if v.get("name") == linkage.name and v.get("version") == linkage.version
        ]
        if not matches:
            return None
        if len(matches) > 1:
            raise LinkageError(
                f"ambiguous template version: {linkage.name} v{linkage.version} "
                f"matches {len(matches)} events"
            )
        return matches[0].get("event_id")
