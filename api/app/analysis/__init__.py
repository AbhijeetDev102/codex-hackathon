"""Deterministic analysis used before any model is asked to explain the data.

Keeping these functions free of HTTP, database, and graph dependencies makes the
important business rules easy to test and reuse.
"""

from .inflections import InflectionCandidate, detect_inflections
from .metrics import MetricPoint, derive_financial_metrics, quarter_over_quarter_change
from .outcomes import OutcomeDecision, assess_outcome
from .verification import ClaimVerification, verify_claim

__all__ = [
    "ClaimVerification",
    "InflectionCandidate",
    "MetricPoint",
    "OutcomeDecision",
    "assess_outcome",
    "derive_financial_metrics",
    "detect_inflections",
    "quarter_over_quarter_change",
    "verify_claim",
]
