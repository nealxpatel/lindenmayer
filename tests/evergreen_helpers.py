"""Shared fixture-event builder for evergreen's query/surface/CLI tests.

One synthetic subgraph, fully signed and deterministic (fixed keypair, fixed
``created_at`` values -- no wall clock, registry precedent), covering all
nine kinds evergreen reads. Reused across ``test_evergreen_query.py``,
``test_evergreen_surface.py``, and ``test_evergreen_cli.py`` so the fixture
shape is defined exactly once.
"""

from __future__ import annotations

import json
from dataclasses import replace

from lindenmayer.core.event import Event
from lindenmayer.core.keys import Keypair
from lindenmayer.evergreen.query import KIND_COMPACTION

BRANCH = "main.demo"
RUN = "run-1"
APPROVER = "a" * 64
TEMPLATE_NAME = "dev-node"


def build_fixture_events(keypair: Keypair) -> dict[str, Event]:
    """Return a name -> signed Event map for one synthetic subgraph:

    - 42010 lifecycle: started then completed
    - 38110 pointer: current (completed) state for ``BRANCH``
    - 42050/38150: one template version + its pointer
    - 42020 run accounting for the one run, linked to that template version
      (its ``template`` tag), for the template -> instance linkage CLI
    - 42030 one subgraph digest
    - 42040/42041: one resolved (approved) request, one still-pending request
    - 42060: one compaction event, summary-of the ``started`` lifecycle event
    """
    pk = keypair.public_key_hex

    def emit(kind: int, tags: list[list[str]], content: str, created_at: int) -> Event:
        return keypair.sign_event(Event.build(pubkey=pk, kind=kind, tags=tags, content=content, created_at=created_at))

    events: dict[str, Event] = {}

    events["lifecycle_started"] = emit(
        42010,
        [["branch", BRANCH], ["status", "started"], ["run", RUN]],
        json.dumps({"reason": ""}),
        1_700_000_000,
    )
    events["lifecycle_completed"] = emit(
        42010,
        [["branch", BRANCH], ["status", "completed"], ["run", RUN]],
        json.dumps({"reason": "done"}),
        1_700_000_100,
    )
    events["state_pointer"] = emit(
        38110,
        [["d", BRANCH], ["status", "completed"], ["run", RUN], ["iter", "3"]],
        json.dumps(
            {
                "cost_shadow_usd": 1.23,
                "cost_cap_usd": 25.0,
                "last_lifecycle_event": events["lifecycle_completed"].id,
            }
        ),
        1_700_000_100,
    )
    events["template_version"] = emit(
        42050,
        [["template_name", TEMPLATE_NAME], ["version", "2"], ["git_ref", "c6696b7"]],
        json.dumps({"summary": "v2"}),
        1_700_000_000,
    )
    events["template_pointer"] = emit(
        38150,
        [["d", TEMPLATE_NAME], ["e", events["template_version"].id]],
        "",
        1_700_000_000,
    )
    events["run_accounting"] = emit(
        42020,
        [["branch", BRANCH], ["run", RUN], ["template", events["template_version"].id]],
        json.dumps({"iter_count": 3, "cost_shadow_usd": 1.23, "duration_s": 120.0, "exit_status": "completed"}),
        1_700_000_100,
    )
    events["subgraph_digest"] = emit(
        42030,
        [["branch", BRANCH], ["period_start", "2026-07-24T00:00:00"], ["period_end", "2026-07-24T01:00:00"]],
        json.dumps(
            {
                "child_count": 1,
                "active": 0,
                "exited": 0,
                "completed": 1,
                "stuck_flagged": 0,
                "subtree_cost_shadow_usd": 1.23,
            }
        ),
        1_700_000_100,
    )
    events["approval_request_resolved"] = emit(
        42040,
        [["branch", BRANCH], ["run", RUN], ["iter", "2"], ["step", "review"], ["p", APPROVER]],
        json.dumps({"step_name": "review", "summary": "merge child work"}),
        1_700_000_050,
    )
    events["approval_verdict"] = emit(
        42041,
        [["e", events["approval_request_resolved"].id], ["verdict", "approve"]],
        json.dumps({"rationale": "looks good"}),
        1_700_000_060,
    )
    events["approval_request_pending"] = emit(
        42040,
        [["branch", BRANCH], ["run", RUN], ["iter", "3"], ["step", "deploy"], ["p", APPROVER]],
        json.dumps({"step_name": "deploy", "summary": "ship to prod"}),
        1_700_000_090,
    )
    events["compaction"] = emit(
        KIND_COMPACTION,
        [
            ["branch", BRANCH],
            ["run", RUN],
            ["iter", "2"],
            ["step", "EXECUTE"],
            ["session", "sess-abc"],
            ["e", events["lifecycle_started"].id, "", "summary-of"],
            ["detection", "harness-marker"],
        ],
        json.dumps({"pre_tokens": 50000, "post_tokens": 8000, "duration_ms": 1200, "summary_hash": "deadbeef" * 8}),
        1_700_000_055,
    )
    return events


def tamper(event: Event) -> Event:
    """A copy of ``event`` with its content mutated post-signing -- ``id``
    and ``sig`` stay as originally signed, so ``id_valid()`` (and therefore
    ``verify()``) fails. Simulates a relay or transport rewriting content
    without the signing key."""
    return replace(event, content=event.content + " ")
