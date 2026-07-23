"""Translation layer: Fractal rows → core kind models.

Maps Fractal DB rows to Lindenmayer's eight custom kinds:
- status transitions → 42010 lifecycle
- one 42020 accounting rollup per run (tokens + shadow cost), NEVER per step or iteration
- subgraph summaries → 42030 digests
- requires_approval flows → 42040/42041
- current node state → 38110

Only persistent, identified nodes author events; ephemeral workers appear solely inside
their parent's digest aggregates.

Acceptance: golden tests (fixture rows → expected signed events) plus explicit tests
that no per-step publication path exists.
"""

from lindenmayer.core.kinds.models import (
    NodeLifecycle,
    RunAccounting,
    SubgraphDigest,
    ApprovalRequest,
    ApprovalVerdict,
    NodeStatePointer,
)


def translate_node_lifecycle(row: dict) -> NodeLifecycle | None:
    """Translate a node status change to kind 42010.

    Args:
        row: Fractal nodes/runs row

    Returns:
        NodeLifecycle model or None if not applicable
    """
    if not row:
        return None

    branch = row.get("node")
    status = row.get("status")
    run = row.get("run")

    if not branch or not status or not run:
        return None

    return NodeLifecycle(
        branch=branch,
        status=status,
        run=run,
        reason=row.get("reason", ""),
        parent_pubkey=row.get("parent_pubkey"),
        prev_event_id=row.get("prev_event_id"),
    )


def translate_run_accounting(row: dict, transcript_usage: dict) -> RunAccounting | None:
    """Translate a run to kind 42020 accounting event (one per run, never per step).

    Args:
        row: Fractal runs row
        transcript_usage: Token usage from transcripts

    Returns:
        RunAccounting model or None
    """
    if not row:
        return None

    branch = row.get("node")
    run = row.get("run")
    status = row.get("status")

    if not branch or not run:
        return None

    exit_status = status if status in ("completed", "exited", "killed") else "exited"

    if not transcript_usage:
        transcript_usage = {}

    cost_shadow_usd = transcript_usage.get("cost_shadow_usd", 0.0)
    iter_count = transcript_usage.get("iter_count", 0)
    duration_s = transcript_usage.get("duration_s", 0.0)

    started_at = row.get("started_at")
    ended_at = row.get("ended_at")
    if started_at and ended_at:
        from datetime import datetime
        try:
            start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            end = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
            duration_s = (end - start).total_seconds()
        except (ValueError, AttributeError):
            pass

    return RunAccounting(
        branch=branch,
        run=run,
        iter_count=iter_count,
        cost_shadow_usd=cost_shadow_usd,
        duration_s=duration_s,
        exit_status=exit_status,
        template=row.get("template"),
    )


def translate_subgraph_digest(row: dict) -> SubgraphDigest | None:
    """Translate subgraph summaries to kind 42030.

    Args:
        row: Fractal node/run row

    Returns:
        SubgraphDigest model or None
    """
    if not row:
        return None

    branch = row.get("node")
    if not branch:
        return None

    period_start = row.get("period_start")
    period_end = row.get("period_end")
    if not period_start or not period_end:
        return None

    return SubgraphDigest(
        branch=branch,
        period_start=period_start,
        period_end=period_end,
        child_count=row.get("child_count", 0),
        active=row.get("active", 0),
        exited=row.get("exited", 0),
        completed=row.get("completed", 0),
        stuck_flagged=row.get("stuck_flagged", 0),
        subtree_cost_shadow_usd=row.get("subtree_cost_shadow_usd", 0.0),
    )


def translate_approval_request(row: dict) -> ApprovalRequest | None:
    """Translate requires_approval step to kind 42040.

    Args:
        row: Fractal steps row

    Returns:
        ApprovalRequest model or None
    """
    if not row:
        return None

    branch = row.get("node")
    run = row.get("run")
    iter_num = row.get("iter")
    step = row.get("step")
    approver_pubkey = row.get("approver_pubkey")
    step_name = row.get("step_name")

    if not all([branch, run, iter_num, step, approver_pubkey, step_name]):
        return None

    return ApprovalRequest(
        branch=branch,
        run=run,
        iter=str(iter_num),
        step=str(step),
        approver_pubkey=approver_pubkey,
        step_name=step_name,
        summary=row.get("summary", ""),
    )


def translate_approval_verdict(row: dict) -> ApprovalVerdict | None:
    """Translate approval outcome to kind 42041.

    Args:
        row: Fractal steps row

    Returns:
        ApprovalVerdict model or None
    """
    if not row:
        return None

    request_id = row.get("request_id")
    verdict = row.get("verdict")

    if not request_id or verdict not in ("approve", "reject"):
        return None

    return ApprovalVerdict(
        request_id=request_id,
        verdict=verdict,
        rationale=row.get("rationale", ""),
    )


def translate_node_state(row: dict) -> NodeStatePointer | None:
    """Translate current node state to kind 38110.

    Args:
        row: Fractal nodes row

    Returns:
        NodeStatePointer model or None
    """
    if not row:
        return None

    branch = row.get("node")
    status = row.get("status")
    run = row.get("run")
    iter_num = row.get("iter")
    last_lifecycle_event = row.get("last_lifecycle_event")

    if not all([branch, status, run, iter_num, last_lifecycle_event]):
        return None

    return NodeStatePointer(
        branch=branch,
        status=status,
        run=run,
        iter=str(iter_num),
        cost_shadow_usd=row.get("cost_shadow_usd", 0.0),
        cost_cap_usd=row.get("cost_cap_usd", 0.0),
        last_lifecycle_event=last_lifecycle_event,
    )
