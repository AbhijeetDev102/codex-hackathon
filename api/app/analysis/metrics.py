"""Small, auditable financial calculations for research runs."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from itertools import pairwise


@dataclass(frozen=True)
class MetricPoint:
    """A single disclosed or derived value for one reporting period."""

    metric: str
    period: str
    value: float
    unit: str = "USD"
    kind: str = "disclosed"
    evidence_id: str | None = None


def _ordered(points: Iterable[MetricPoint]) -> list[MetricPoint]:
    """Sort ISO-like quarter/date labels in their natural reporting order."""

    return sorted(points, key=lambda point: point.period)


def quarter_over_quarter_change(points: Iterable[MetricPoint]) -> list[MetricPoint]:
    """Return percentage change points without fabricating a value for zero bases.

    A zero prior period makes a percentage mathematically misleading, so that
    comparison is intentionally omitted instead of using an arbitrary divisor.
    """

    ordered = _ordered(points)
    changes: list[MetricPoint] = []
    for previous, current in pairwise(ordered):
        if previous.value == 0:
            continue
        changes.append(
            MetricPoint(
                metric=f"{current.metric}_qoq_change",
                period=current.period,
                value=(current.value - previous.value) / abs(previous.value),
                unit="ratio",
                kind="derived",
                evidence_id=current.evidence_id,
            )
        )
    return changes


def derive_financial_metrics(points: Iterable[MetricPoint]) -> list[MetricPoint]:
    """Produce transparent derived metrics alongside—not in place of—filing values.

    `cash_burn` is derived from a negative operating cash-flow value. Positive cash
    flow is deliberately not presented as a negative burn number.
    """

    ordered = list(points)
    derived: list[MetricPoint] = []
    for point in ordered:
        if point.metric == "operating_cash_flow" and point.value < 0:
            derived.append(
                MetricPoint(
                    metric="cash_burn",
                    period=point.period,
                    value=abs(point.value),
                    unit=point.unit,
                    kind="derived",
                    evidence_id=point.evidence_id,
                )
            )

    by_metric: dict[str, list[MetricPoint]] = {}
    for point in ordered:
        if point.metric in {"revenue", "cash", "net_loss", "operating_cash_flow"}:
            by_metric.setdefault(point.metric, []).append(point)
    for values in by_metric.values():
        derived.extend(quarter_over_quarter_change(values))
    return derived
