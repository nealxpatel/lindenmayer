"""Publish template versions as kind 42050/38150 events.

Reads a template directory, derives name/version/git_ref from content and commit
pin, and emits 42050 (append-only version) + 38150 (addressable pointer) events.
Event ids are deterministic from git commit data (source timestamps, never wall
clock — the bridge precedent, verdict 8266A685).
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from lindenmayer.core.event import Event

__all__ = ["TemplatePublisher", "PublisherError"]


class PublisherError(Exception):
    """Template publisher operation failed."""

    pass


@dataclass
class TemplateInfo:
    """Extracted metadata from a template directory."""

    name: str
    version: str
    git_ref: str
    created_at: int


def _extract_version_from_readme(readme_path: Path) -> str:
    """Extract version from README.md (e.g., 'Template (v1)' -> '1')."""
    try:
        content = readme_path.read_text()
        import re

        match = re.search(r"\(v(\d+(?:\.\d+)*)\)", content)
        if match:
            return match.group(1)
    except Exception:
        pass
    return "1.0.0"


def _get_git_commit_info(template_dir: Path) -> tuple[str, int]:
    """Get the git commit sha and timestamp for the template directory.

    Returns:
        (commit_sha, unix_timestamp)

    Raises:
        PublisherError: If git operations fail
    """
    try:
        # Get the most recent commit touching this template
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H %ct", str(template_dir)],
            cwd=template_dir.parent.parent.parent,  # repo root
            capture_output=True,
            text=True,
            check=True,
        )
        parts = result.stdout.strip().split()
        if len(parts) < 2:
            raise PublisherError(f"cannot parse git log output: {result.stdout}")
        sha = parts[0]
        timestamp = int(parts[1])
        return sha, timestamp
    except subprocess.CalledProcessError as e:
        raise PublisherError(f"git log failed: {e.stderr}") from e


class TemplatePublisher:
    """Publish template versions to a relay."""

    def __init__(self, repo_root: Path, keypair) -> None:
        """Initialize publisher.

        Args:
            repo_root: Path to repository root (contains tree/templates/)
            keypair: Keypair for signing events
        """
        self._repo_root = repo_root
        self._keypair = keypair

    def extract_template_info(self, template_dir: Path) -> TemplateInfo:
        """Extract name, version, git_ref from a template directory.

        Args:
            template_dir: Path to template directory (e.g., tree/templates/dev-node)

        Returns:
            TemplateInfo with extracted metadata

        Raises:
            PublisherError: If extraction fails
        """
        # Name from directory
        name = template_dir.name
        if not name:
            raise PublisherError(f"invalid template path: {template_dir}")

        # Version from README
        readme = template_dir / "README.md"
        if not readme.exists():
            raise PublisherError(f"README.md not found in {template_dir}")
        version = _extract_version_from_readme(readme)

        # Git commit and timestamp
        sha, created_at = _get_git_commit_info(template_dir)
        git_ref = sha[:7]  # Short ref for readability; full sha is the source of truth

        return TemplateInfo(name=name, version=version, git_ref=git_ref, created_at=created_at)

    def build_version_event(self, template_info: TemplateInfo, summary: str = "") -> Event:
        """Build a kind 42050 (Template Version) event.

        Args:
            template_info: Extracted template metadata
            summary: Human-readable summary of changes

        Returns:
            Unsigned Event ready to sign
        """
        if not summary:
            summary = f"Release of {template_info.name} v{template_info.version}"

        tags = [
            ["template_name", template_info.name],
            ["version", template_info.version],
            ["git_ref", template_info.git_ref],
        ]

        content = json.dumps({"summary": summary}, ensure_ascii=False)

        return Event.build(
            pubkey=self._keypair.public_key_hex,
            kind=42050,
            tags=tags,
            content=content,
            created_at=template_info.created_at,
        )

    def build_pointer_event(self, version_event: Event) -> Event:
        """Build a kind 38150 (Template Pointer) event pointing to a version.

        Args:
            version_event: The kind 42050 event this pointer should reference

        Returns:
            Unsigned Event ready to sign
        """
        template_name = version_event.first_tag_value("template_name")
        if not template_name:
            raise PublisherError("version event missing template_name tag")

        tags = [
            ["d", template_name],
            ["e", version_event.id],
        ]

        return Event.build(
            pubkey=self._keypair.public_key_hex,
            kind=38150,
            tags=tags,
            content="",
            created_at=version_event.created_at,
        )
