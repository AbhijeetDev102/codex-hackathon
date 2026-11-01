"""Deterministic claim guards used before an LLM entailment check."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class ClaimVerification:
    result: str
    reason: str
    cited_evidence: list[str]


def _numbers(text: str) -> set[str]:
    return set(re.findall(r"(?<![A-Za-z])\d+(?:[,.]\d+)?%?", text))


def verify_claim(
    claim_text: str,
    cited_evidence: Sequence[str],
    evidence_by_id: Mapping[str, str],
) -> ClaimVerification:
    """Reject claims lacking valid citations or unsupported numeric assertions.

    This is not semantic fact checking. Its job is to stop obviously ungrounded
    content before the later reasoning verifier decides whether a source entails a
    statement.
    """

    citations = list(dict.fromkeys(cited_evidence))
    if not citations:
        return ClaimVerification("unsupported", "The claim has no evidence citation.", citations)
    missing = [item for item in citations if item not in evidence_by_id]
    if missing:
        return ClaimVerification(
            "unsupported", f"The claim cites evidence not available in this run: {', '.join(missing)}.", citations
        )
    source_text = " ".join(evidence_by_id[item] for item in citations).lower()
    claim_numbers = _numbers(claim_text)
    source_numbers = _numbers(source_text)
    if not claim_numbers.issubset(source_numbers):
        unsupported = sorted(claim_numbers - source_numbers)
        return ClaimVerification(
            "unsupported",
            f"The cited evidence does not contain the claim's numeric values: {', '.join(unsupported)}.",
            citations,
        )
    return ClaimVerification("supported", "Citation and numeric guards passed.", citations)
