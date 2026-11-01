"""The explicit shared state passed between research graph nodes."""

from __future__ import annotations

import operator
from typing import Annotated, Any

from typing_extensions import TypedDict


def merge_statuses(current: dict[str, str], update: dict[str, str]) -> dict[str, str]:
    """Allow parallel graph branches to publish distinct node states safely."""

    return {**current, **update}


class RunState(TypedDict, total=False):
    run_id: str
    company: dict[str, Any]
    sources: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    events: list[dict[str, Any]]
    metrics: list[dict[str, Any]]
    outcome: dict[str, Any]
    inflections: list[dict[str, Any]]
    hypotheses: list[dict[str, Any]]
    claims: list[dict[str, Any]]
    rejected_claims: list[dict[str, Any]]
    verification: dict[str, Any]
    pattern_match: dict[str, Any] | None
    patterns: list[dict[str, Any]]
    report: dict[str, Any] | None
    revise_round: int
    node_status: Annotated[dict[str, str], merge_statuses]
    errors: Annotated[list[str], operator.add]
