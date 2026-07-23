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
    pass


def translate_run_accounting(row: dict, transcript_usage: dict) -> RunAccounting | None:
    """Translate a run to kind 42020 accounting event (one per run, never per step).

    Args:
        row: Fractal runs row
        transcript_usage: Token usage from transcripts

    Returns:
        RunAccounting model or None
    """
    pass


def translate_subgraph_digest(row: dict) -> SubgraphDigest | None:
    """Translate subgraph summaries to kind 42030.

    Args:
        row: Fractal node/run row

    Returns:
        SubgraphDigest model or None
    """
    pass


def translate_approval_request(row: dict) -> ApprovalRequest | None:
    """Translate requires_approval step to kind 42040.

    Args:
        row: Fractal steps row

    Returns:
        ApprovalRequest model or None
    """
    pass


def translate_approval_verdict(row: dict) -> ApprovalVerdict | None:
    """Translate approval outcome to kind 42041.

    Args:
        row: Fractal steps row

    Returns:
        ApprovalVerdict model or None
    """
    pass


def translate_node_state(row: dict) -> NodeStatePointer | None:
    """Translate current node state to kind 38110.

    Args:
        row: Fractal nodes row

    Returns:
        NodeStatePointer model or None
    """
    pass
