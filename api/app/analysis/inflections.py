"""Robust, explainable turning-point detection."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from statistics import median

from .metrics import MetricPoint, quarter_over_quarter_change


@dataclass(frozen=True)
class InflectionCandidate:
    period: str
    metric: str
    size: float
    robust_z_score: float
    explanation: str
    evidence_ids: list[str]


def _robust_z_score(value: float, values: list[float]) -> float | None:
    """Return MAD-based z score, or None when a stable baseline is unavailable."""

    if len(values) < 3:
        return None
    center = median(values)
    deviations = [abs(item - center) for item in values]
    mad = median(deviations)
    if mad == 0:
        return None
    return 0.6745 * (value - center) / mad


def detect_inflections(
    metrics: Iterable[MetricPoint],
    *,
    window: int = 8,
    min_periods: int = 6,
    threshold: float = 3.0,
) -> list[InflectionCandidate]:
    """Flag unusual quarter-on-quarter changes using a rolling MAD baseline.

    This deliberately identifies *when* a change is unusual. It never describes
    the finding as a cause; a later evidence-backed explanation step does that.
    """

    by_metric: dict[str, list[MetricPoint]] = {}
    for metric in metrics:
        if metric.metric in {"revenue", "cash", "net_loss", "operating_cash_flow"}:
            by_metric.setdefault(metric.metric, []).append(metric)

    candidates: list[InflectionCandidate] = []
    for name, values in by_metric.items():
        changes = quarter_over_quarter_change(values)
        for index, change in enumerate(changes):
            baseline_start = max(0, index - window)
            baseline = [item.value for item in changes[baseline_start:index]]
            if len(baseline) < min_periods:
                continue
            score = _robust_z_score(change.value, baseline)
            if score is None or abs(score) < threshold:
                continue
            direction = "increased" if change.value > 0 else "decreased"
            candidates.append(
                InflectionCandidate(
                    period=change.period,
                    metric=name,
                    size=change.value,
                    robust_z_score=score,
                    explanation=(
                        f"{name.replace('_', ' ').title()} {direction} "
                        f"{abs(change.value):.0%} quarter over quarter; this is an unusual "
                        "change, not proof of cause."
                    ),
                    evidence_ids=[change.evidence_id] if change.evidence_id else [],
                )
            )
    return sorted(candidates, key=lambda item: abs(item.robust_z_score), reverse=True)
