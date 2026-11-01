"""Evidence-linked business outcome rules.

The classifier is intentionally conservative: a company in distress is not called a
failure unless a filing or verified event supports that finding.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

OUTCOME_STATUSES = {
    "bankruptcy",
    "delisted",
    "wound_down",
    "going_concern",
    "distress_without_failure",
    "unknown",
}


@dataclass(frozen=True)
class OutcomeDecision:
    status: str
    summary: str
    evidence_ids: list[str]
    confidence: str
    verified: bool


def _normalise_event(event: Mapping[str, object]) -> tuple[str, list[str], bool]:
    parts = [
        str(event.get("category", "")),
        str(event.get("description", "")),
        str(event.get("form", "")),
        str(event.get("item", "")),
        str(event.get("text", "")),
    ]
    evidence = [str(item) for item in event.get("evidence_ids", []) if item]
    return " ".join(parts).lower(), evidence, bool(event.get("verified", False))


def assess_outcome(
    events: Iterable[Mapping[str, object]],
    *,
    financial_stress: bool = False,
) -> OutcomeDecision:
    """Classify an outcome from verified filing/event evidence in priority order."""

    normalized = [_normalise_event(event) for event in events]
    rules = (
        (
            "bankruptcy",
            ("chapter 11", "chapter 7", "bankruptcy", "voluntary petition", "8-k item 1.03"),
            "Verified filing evidence indicates a bankruptcy proceeding.",
        ),
        (
            "delisted",
            ("delisted", "delisting", "8-k item 3.01", "suspension from trading"),
            "Verified filing evidence indicates a delisting or trading suspension.",
        ),
        (
            "wound_down",
            ("wind down", "winding down", "cease operations", "liquidat", "dissolution"),
            "Verified evidence indicates operations were wound down or liquidated.",
        ),
        (
            "going_concern",
            ("substantial doubt", "going concern"),
            "Verified filing evidence contains a going-concern warning.",
        ),
    )
    for status, phrases, summary in rules:
        matching = [(evidence, verified) for text, evidence, verified in normalized if any(phrase in text for phrase in phrases)]
        if matching:
            evidence_ids = list(dict.fromkeys(item for evidence, _ in matching for item in evidence))
            verified = any(verified for _, verified in matching)
            return OutcomeDecision(
                status=status,
                summary=summary,
                evidence_ids=evidence_ids,
                confidence="high" if verified else "moderate",
                verified=verified,
            )
    if financial_stress:
        return OutcomeDecision(
            status="distress_without_failure",
            summary="The available data shows financial stress but no verified failure outcome.",
            evidence_ids=[],
            confidence="moderate",
            verified=False,
        )
    return OutcomeDecision(
        status="unknown",
        summary="The available evidence does not support a specific business outcome.",
        evidence_ids=[],
        confidence="insufficient",
        verified=False,
    )
