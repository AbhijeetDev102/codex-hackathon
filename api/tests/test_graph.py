import pytest

from app.graph import build_research_graph, nodes
from app.graph.runner import _match_patterns


@pytest.mark.asyncio
async def test_graph_never_reports_unsupported_claims():
    graph = build_research_graph()
    result = await graph.ainvoke(
        {
            "run_id": "run-1",
            "company": {"legal_name": "Example Co."},
            "evidence": [{"evidence_key": "E-001", "text": "Cash fell to 10 in 2024."}],
            "events": [],
            "metrics": [],
            "hypotheses": [],
            "claims": [
                {"text": "Cash fell to 10 in 2024.", "cited_evidence": ["E-001"]},
                {"text": "The chief executive caused the collapse.", "cited_evidence": []},
            ],
            "revise_round": 0,
        }
    )
    assert result["verification"]["removed"] == 1
    assert result["revise_round"] == 1
    assert [claim["text"] for claim in result["claims"]] == ["Cash fell to 10 in 2024."]
    assert result["report"] is not None
    assert [claim["text"] for claim in result["report"]["claims"]] == ["Cash fell to 10 in 2024."]
    assert result["node_status"]["write_report"] == "done"


@pytest.mark.asyncio
async def test_repeated_rejections_stop_after_two_revision_rounds():
    async def propose_the_same_unsupported_claim(_: dict) -> dict:
        return {
            "claims": [
                {"text": "An unsupported causal conclusion.", "cited_evidence": []},
            ]
        }

    graph = build_research_graph({"propose_hypotheses": propose_the_same_unsupported_claim})
    result = await graph.ainvoke(
        {
            "run_id": "run-2",
            "company": {"legal_name": "Example Co."},
            "evidence": [],
            "events": [],
            "metrics": [],
            "hypotheses": [],
            "claims": [],
            "revise_round": 0,
        }
    )
    assert result["revise_round"] == 2
    assert result["claims"] == []
    assert result["report"]["claims"] == []


@pytest.mark.asyncio
async def test_live_metric_evidence_keys_survive_inflection_detection():
    values = [100.0, 101.0, 103.02, 103.02, 106.1106, 108.232812, 109.31514012, 21.863028024]
    state = {
        "metrics": [
            {
                "metric": "revenue",
                "period": f"202{index // 4}-Q{index % 4 + 1}",
                "value": value,
                "kind": "disclosed",
                "evidence_key": f"E-{index + 1:03d}",
            }
            for index, value in enumerate(values)
        ]
    }
    result = await nodes.detect_inflections_node(state)
    assert result["inflections"]
    assert result["inflections"][0]["evidence_ids"] == ["E-008"]


@pytest.mark.asyncio
async def test_distress_outcome_keeps_financial_receipts():
    result = await nodes.assess_outcome_node(
        {
            "events": [],
            "metrics": [
                {"metric": "cash", "period": "2023-Q1", "value": 100, "evidence_key": "E-001"},
                {"metric": "cash", "period": "2023-Q2", "value": 20, "evidence_key": "E-002"},
                {"metric": "net_loss", "period": "2023-Q2", "value": -50, "evidence_key": "E-003"},
            ],
        }
    )
    assert result["outcome"]["status"] == "distress_without_failure"
    assert result["outcome"]["evidence_ids"] == ["E-001", "E-002", "E-003"]


@pytest.mark.asyncio
async def test_local_pattern_match_returns_comparable_cases_and_reaches_report():
    changes = await _match_patterns(
        {
            "company": {"legal_name": "Example Co."},
            "hypotheses": [
                {
                    "mechanism": "Cash decline and a going-concern disclosure increased restructuring pressure."
                }
            ],
            "events": [],
        }
    )
    match = changes["pattern_match"]
    assert match is not None
    assert match["archetype_key"] == "fixed_cost_liquidity_crunch"
    assert len(match["similar_cases"]) == 2
    assert all(case["similarity"] and case["difference"] for case in match["similar_cases"])

    report = await nodes.write_report_node({"pattern_match": match, "claims": []})
    assert report["report"]["pattern_match"] == match
