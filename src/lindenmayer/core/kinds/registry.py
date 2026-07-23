"""Kind registry: kind number -> model class, plus the parse dispatcher."""

from __future__ import annotations

from lindenmayer.core.event import Event
from lindenmayer.core.kinds import constants
from lindenmayer.core.kinds.base import KindModel, KindValidationError
from lindenmayer.core.kinds.models import (
    ApprovalRequest,
    ApprovalVerdict,
    NodeLifecycle,
    NodeStatePointer,
    RunAccounting,
    SubgraphDigest,
    TemplatePointer,
    TemplateVersion,
)

__all__ = ["KIND_REGISTRY", "parse_event"]

KIND_REGISTRY: dict[int, type[KindModel]] = {
    constants.KIND_NODE_LIFECYCLE: NodeLifecycle,
    constants.KIND_RUN_ACCOUNTING: RunAccounting,
    constants.KIND_SUBGRAPH_DIGEST: SubgraphDigest,
    constants.KIND_APPROVAL_REQUEST: ApprovalRequest,
    constants.KIND_APPROVAL_VERDICT: ApprovalVerdict,
    constants.KIND_TEMPLATE_VERSION: TemplateVersion,
    constants.KIND_NODE_STATE_POINTER: NodeStatePointer,
    constants.KIND_TEMPLATE_POINTER: TemplatePointer,
}


def parse_event(event: Event) -> KindModel:
    """Dispatch a wire event to its kind model, validating fully.

    Raises ``KindValidationError`` for unknown kinds or schema violations.
    """
    model_cls = KIND_REGISTRY.get(event.kind)
    if model_cls is None:
        raise KindValidationError(
            f"kind {event.kind} is not a Lindenmayer kind "
            f"(known: {sorted(KIND_REGISTRY)})"
        )
    return model_cls.from_event(event)
