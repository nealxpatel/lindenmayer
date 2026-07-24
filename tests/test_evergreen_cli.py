"""CLI-invocation E2E: spawn the actual `lindenmayer.evergreen.cli` module
entry point as a subprocess with real argv, for every subcommand, against a
running MockRelay. This exercises the argparse path itself, not just the
functions behind it -- both prior ply nodes (bridge, registry) shipped CLIs
whose argument path no test ever executed, and both broke on first live use
(tree/evergreen/NODE.md deliverable 3)."""

from __future__ import annotations

import asyncio
import sys

import pytest

from evergreen_helpers import BRANCH, build_fixture_events
from lindenmayer.core.keys import Keypair
from relay_mock import MockRelay


async def _run_cli(relay_url: str, *args: str) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "lindenmayer.evergreen.cli",
        "--relay",
        relay_url,
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=20)
    return proc.returncode, stdout.decode(), stderr.decode()


@pytest.fixture
def keypair() -> Keypair:
    return Keypair.generate()


@pytest.mark.asyncio
async def test_cli_runs_subcommand(keypair: Keypair):
    async with MockRelay() as relay:
        events = build_fixture_events(keypair)
        for event in events.values():
            relay.events.append(event.to_dict())
        code, out, err = await _run_cli(relay.url, "runs", BRANCH)
    assert code == 0, err
    assert "run-1" in out
    assert "completed" in out
    assert "shadow cost" in out


@pytest.mark.asyncio
async def test_cli_cost_subcommand(keypair: Keypair):
    async with MockRelay() as relay:
        events = build_fixture_events(keypair)
        for event in events.values():
            relay.events.append(event.to_dict())
        code, out, err = await _run_cli(relay.url, "cost", BRANCH)
    assert code == 0, err
    assert "shadow cost" in out
    assert "$1.23" in out or "1.2300" in out
    assert "TOTAL" in out


@pytest.mark.asyncio
async def test_cli_approvals_subcommand(keypair: Keypair):
    async with MockRelay() as relay:
        events = build_fixture_events(keypair)
        for event in events.values():
            relay.events.append(event.to_dict())
        code, out, err = await _run_cli(relay.url, "approvals", BRANCH)
    assert code == 0, err
    assert "review" in out
    assert "approved" in out
    assert "deploy" in out
    assert "pending" in out


@pytest.mark.asyncio
async def test_cli_templates_subcommand(keypair: Keypair):
    async with MockRelay() as relay:
        events = build_fixture_events(keypair)
        for event in events.values():
            relay.events.append(event.to_dict())
        code, out, err = await _run_cli(relay.url, "templates", BRANCH)
    assert code == 0, err
    assert "dev-node" in out
    assert "v2" in out
    assert "c6696b7" in out


@pytest.mark.asyncio
async def test_cli_unknown_branch_reports_empty_not_error(keypair: Keypair):
    async with MockRelay() as relay:
        code, out, err = await _run_cli(relay.url, "runs", "main.nonexistent")
    assert code == 0, err
    assert "No runs found" in out


@pytest.mark.asyncio
async def test_cli_no_subcommand_prints_help():
    """Argument-path sanity: bare invocation (no subcommand) exits 0 and
    prints usage rather than crashing -- covers `main()`'s own argv handling,
    not just `main_async`."""
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "lindenmayer.evergreen.cli",
        "--relay",
        "ws://localhost:1",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=20)
    assert proc.returncode == 0
    assert b"usage" in stdout.lower() or b"usage" in stderr.lower()


@pytest.mark.asyncio
async def test_cli_missing_relay_arg_errors():
    """Argument-path sanity: a required arg omitted fails argparse's own
    parsing (exit code 2), before any relay connection is attempted."""
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "lindenmayer.evergreen.cli",
        "runs",
        "main.demo",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=20)
    assert proc.returncode == 2
    assert b"--relay" in stderr
