"""Command-line interface for template registry operations.

Commands:
  publish <template_dir> - Publish a template version to the relay
  list <author>          - List all templates from an author
  show <author> <name>   - Show version history for a template
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from lindenmayer.core.config import CoreConfig
from lindenmayer.core.keys import Keypair
from lindenmayer.core.relay import RelayClient
from lindenmayer.registry.publisher import TemplatePublisher
from lindenmayer.registry.reader import TemplateReader

__all__ = ["main"]


def _create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="lindenmayer-registry",
        description="Lindenmayer template registry: publish and query template versions",
    )

    parser.add_argument(
        "--relay",
        default="ws://localhost:8080",
        help="Relay URL (default: ws://localhost:8080)",
    )
    parser.add_argument(
        "--secret",
        help="Keypair secret hex (default: generate random)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # publish command
    publish_parser = subparsers.add_parser("publish", help="Publish a template version")
    publish_parser.add_argument("template_dir", help="Path to template directory")
    publish_parser.add_argument("--summary", help="Summary of changes")

    # list command
    list_parser = subparsers.add_parser("list", help="List templates from an author")
    list_parser.add_argument("author", help="Author pubkey")

    # show command
    show_parser = subparsers.add_parser("show", help="Show version history for a template")
    show_parser.add_argument("author", help="Author pubkey")
    show_parser.add_argument("name", help="Template name")

    return parser


async def _cmd_publish(args) -> int:
    """Execute publish command."""
    try:
        template_dir = Path(args.template_dir).resolve()
        if not template_dir.is_dir():
            print(f"error: template directory not found: {template_dir}", file=sys.stderr)
            return 1

        # Get keypair
        if args.secret:
            keypair = Keypair.from_hex(args.secret)
        else:
            keypair = Keypair.generate()
            print(f"Generated keypair: {keypair.public_key_hex}", file=sys.stderr)

        # Create publisher
        repo_root = template_dir.parent.parent.parent
        publisher = TemplatePublisher(repo_root, keypair)

        # Extract template info
        template_info = publisher.extract_template_info(template_dir)
        print(f"Publishing {template_info.name} v{template_info.version}")

        # Build events
        version_event = publisher.build_version_event(
            template_info, summary=args.summary or ""
        )
        pointer_event = publisher.build_pointer_event(version_event)

        # Sign events
        signed_version = keypair.sign_event(version_event)
        signed_pointer = keypair.sign_event(pointer_event)

        # Publish to relay
        config = CoreConfig(relay_url=args.relay)
        async with RelayClient(args.relay, keypair, config) as client:
            await client.publish(signed_version)
            print(f"Published version event: {signed_version.id}")

            await client.publish(signed_pointer)
            print(f"Published pointer event: {signed_pointer.id}")

        return 0
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


async def _cmd_list(args) -> int:
    """Execute list command."""
    try:
        keypair = Keypair.generate()
        config = CoreConfig(relay_url=args.relay)

        async with RelayClient(args.relay, keypair, config) as client:
            reader = TemplateReader(client)

            # Query for all kind 42050 events by this author
            filters = [{"kinds": [42050], "authors": [args.author]}]
            events = await client.query(filters)

            # Group by template name
            templates: dict[str, list] = {}
            for event in events:
                name = event.first_tag_value("template_name")
                if name:
                    if name not in templates:
                        templates[name] = []
                    templates[name].append(event)

            if not templates:
                print("No templates found for this author")
                return 0

            for name in sorted(templates.keys()):
                versions = templates[name]
                print(f"{name}:")
                for event in sorted(versions, key=lambda e: e.first_tag_value("version") or ""):
                    version = event.first_tag_value("version")
                    git_ref = event.first_tag_value("git_ref")
                    print(f"  v{version} @ {git_ref}")

        return 0
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


async def _cmd_show(args) -> int:
    """Execute show command."""
    try:
        keypair = Keypair.generate()
        config = CoreConfig(relay_url=args.relay)

        async with RelayClient(args.relay, keypair, config) as client:
            reader = TemplateReader(client)
            versions = await reader.get_version_history(args.author, args.name)

            if not versions:
                print(f"No versions found for {args.name}")
                return 0

            print(f"Template: {args.name}")
            print(f"Author: {args.author}")
            print(f"\nVersion history ({len(versions)} total):")
            for v in versions:
                print(f"  v{v.version} @ {v.git_ref}")
                print(f"    Event: {v.event_id}")
                print(f"    Date:  {v.created_at} ({v.created_at})")
                if v.summary:
                    print(f"    Summary: {v.summary}")
                if v.parent_version_id:
                    print(f"    Parent: {v.parent_version_id}")

        return 0
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


async def main_async(args) -> int:
    """Execute the appropriate command."""
    if not args.command:
        return 1

    if args.command == "publish":
        return await _cmd_publish(args)
    elif args.command == "list":
        return await _cmd_list(args)
    elif args.command == "show":
        return await _cmd_show(args)
    else:
        print(f"unknown command: {args.command}", file=sys.stderr)
        return 1


def main() -> None:
    """Entry point."""
    parser = _create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    exit_code = asyncio.run(main_async(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
