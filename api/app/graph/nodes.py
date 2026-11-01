"""Default graph nodes that are deterministic and safe to exercise in replay mode."""

from __future__ import annotations

from typing import Any

from ..analysis import (
    MetricPoint,
    assess_outcome,
    derive_financial_metrics,
    detect_inflections,
    verify_claim,
)
from .state import RunState


def _metric_points(state: RunState) -> list[MetricPoint]:
    points: list[MetricPoint] = []
    for item in state.get("metrics", []):
        if item.get("kind") == "derived":
            continue
        try:
            points.append(
                MetricPoint(
                    metric=str(item["metric"]),
                    period=str(item["period"]),
                    value=float(item["value"]),
                    unit=str(item.get("unit", "USD")),
                    kind=str(item.get("kind", "disclosed")),
                    # Live SEC collection emits the human-readable receipt as
                    # ``evidence_key``; persisted and replay rows use
                    # ``evidence_id``. Preserve either form through derived
                    # metrics and turning-point detection.
                    evidence_id=item.get("evidence_id") or item.get("evidence_key"),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return points


async def compute_financials(state: RunState) -> dict[str, Any]:
    """Append derived metrics while preserving every disclosed filing value."""

    existing = state.get("metrics", [])
    disclosed = _metric_points(state)
    derived = derive_financial_metrics(disclosed)
    derived_rows = [
        {
            "metric": point.metric,
            "period": point.period,
            "value": point.value,
            "unit": point.unit,
            "kind": point.kind,
            "evidence_id": point.evidence_id,
        }
        for point in derived
    ]
    already_present = {(item.get("metric"), item.get("period")) for item in existing}
    return {"metrics": existing + [row for row in derived_rows if (row["metric"], row["period"]) not in already_present]}


async def assess_outcome_node(state: RunState) -> dict[str, Any]:
    """Return conservative outcome assessment based on events and financial stress."""

    metrics = _metric_points(state)
    cash_points = [point for point in metrics if point.metric == "cash"]
    losses = [point for point in metrics if point.metric == "net_loss" and point.value < 0]
    cash_declining = len(cash_points) >= 2 and cash_points[-1].value < cash_points[0].value
    decision = assess_outcome(state.get("events", []), financial_stress=bool(losses and cash_declining))
    # Stress is a supported finding, not a failure label. When the deterministic
    # rule reaches that result, preserve the filing receipts behind the declining
    # cash and losses so the outcome remains traceable in the API and report.
    evidence_ids = decision.evidence_ids
    if decision.status == "distress_without_failure" and not evidence_ids:
        evidence_ids = list(
            dict.fromkeys(
                point.evidence_id
                for point in [*cash_points, *losses]
                if point.evidence_id
            )
        )
    return {
        "outcome": {
            "status": decision.status,
            "summary": decision.summary,
            "evidence_ids": evidence_ids,
            "confidence": decision.confidence,
            "verified": decision.verified,
        }
    }


async def detect_inflections_node(state: RunState) -> dict[str, Any]:
    candidates = detect_inflections(_metric_points(state))
    return {
        "inflections": [
            {
                "period": item.period,
                "metric": item.metric,
                "size": item.size,
                "explanation": item.explanation,
                "evidence_ids": item.evidence_ids,
            }
            for item in candidates
        ]
    }


async def verify_claims_node(state: RunState) -> dict[str, Any]:
    """Keep only claims that pass deterministic citation guards.

    A configured reasoning provider can add semantic entailment before this node's
    result is persisted; this baseline prevents an ungrounded claim from surviving
    even when that provider is unavailable.
    """

    evidence_by_id: dict[str, str] = {}
    for item in state.get("evidence", []):
        text = str(item.get("text", ""))
        for key in (item.get("id"), item.get("evidence_key")):
            if key:
                evidence_by_id[str(key)] = text
    approved: list[dict[str, Any]] = []
    newly_rejected: list[dict[str, Any]] = []
    prior_rejected = list(state.get("rejected_claims", []))
    for claim in state.get("claims", []):
        result = verify_claim(
            str(claim.get("text", "")),
            [str(item) for item in claim.get("cited_evidence", [])],
            evidence_by_id,
        )
        checked = {**claim, "result": result.result, "reason": result.reason, "cited_evidence": result.cited_evidence}
        if result.result == "supported":
            approved.append(checked)
        else:
            newly_rejected.append(checked)
    rejected = [*prior_rejected, *newly_rejected]
    blockers = bool(newly_rejected) and state.get("revise_round", 0) < 2
    return {
        # Later nodes receive only approved claims. Rejected claims are retained in
        # a separate audit field so their removal can be counted and inspected.
        "claims": approved,
        "rejected_claims": rejected,
        "verification": {
            "checked": len(approved) + len(rejected),
            "supported": len(approved),
            "removed": len(rejected),
            "blockers": blockers,
        },
        "revise_round": state.get("revise_round", 0) + (1 if blockers else 0),
    }


async def write_report_node(state: RunState) -> dict[str, Any]:
    """Build a conservative report from supported claims only."""

    approved_claims = list(state.get("claims", []))
    return {
        "report": {
            "company": state.get("company", {}),
            "outcome": state.get("outcome"),
            "timeline": state.get("events", []),
            "financials": state.get("metrics", []),
            "inflections": state.get("inflections", []),
            "hypotheses": state.get("hypotheses", []),
            "pattern_match": state.get("pattern_match"),
            "claims": approved_claims,
            "verification": state.get("verification", {}),
            "limitations": "Findings identify likely contributors from public evidence; they do not prove causation and are not financial advice.",
        }
    }


async def passthrough(_: RunState) -> dict[str, Any]:
    """Placeholder for providers that are intentionally optional in replay mode."""

    return {}
