from app.analysis import (
    MetricPoint,
    assess_outcome,
    derive_financial_metrics,
    detect_inflections,
    verify_claim,
)


def test_derived_burn_and_quarter_changes_remain_explicitly_derived():
    disclosed = [
        MetricPoint("operating_cash_flow", "2023-Q1", -20.0, evidence_id="E-001"),
        MetricPoint("operating_cash_flow", "2023-Q2", -30.0, evidence_id="E-002"),
    ]
    derived = derive_financial_metrics(disclosed)
    burns = [point for point in derived if point.metric == "cash_burn"]
    changes = [point for point in derived if point.metric == "operating_cash_flow_qoq_change"]
    assert [point.value for point in burns] == [20.0, 30.0]
    assert all(point.kind == "derived" for point in derived)
    assert changes[0].value == -0.5


def test_outcome_requires_evidence_and_prefers_bankruptcy():
    decision = assess_outcome(
        [
            {
                "category": "SEC filing",
                "description": "The company filed a voluntary Chapter 11 petition.",
                "evidence_ids": ["E-004"],
                "verified": True,
            }
        ]
    )
    assert decision.status == "bankruptcy"
    assert decision.evidence_ids == ["E-004"]
    assert decision.verified is True

    distress = assess_outcome([], financial_stress=True)
    assert distress.status == "distress_without_failure"


def test_mad_inflection_detection_uses_historical_baseline():
    revenue = [100.0, 101.0, 103.02, 103.02, 106.1106, 108.232812, 109.31514012, 21.863028024]
    points = [MetricPoint("revenue", f"202{index // 4}-Q{index % 4 + 1}", value, evidence_id="E-010") for index, value in enumerate(revenue)]
    found = detect_inflections(points)
    assert len(found) == 1
    assert found[0].metric == "revenue"
    assert found[0].size < -0.7
    assert "not proof of cause" in found[0].explanation


def test_claim_guard_rejects_unknown_citation_and_number():
    evidence = {"E-001": "Revenue fell to $100 million in 2023."}
    assert verify_claim("Revenue fell to $100 million in 2023.", ["E-001"], evidence).result == "supported"
    assert verify_claim("Revenue fell to $200 million in 2023.", ["E-001"], evidence).result == "unsupported"
    assert verify_claim("Revenue fell.", ["E-999"], evidence).result == "unsupported"
