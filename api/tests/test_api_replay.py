"""End-to-end replay API test for the demo's trust-critical user journey."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_replay_run_exposes_evidence_outcome_and_grounded_chat() -> None:
    with TestClient(app) as client:
        companies = client.get("/api/companies/search", params={"q": "WeWork"})
        assert companies.status_code == 200
        company = companies.json()["results"][0]

        created = client.post("/api/research", json={"company_id": company["id"]})
        assert created.status_code == 202
        run_id = created.json()["id"]

        status = client.get(f"/api/research/{run_id}")
        assert status.json()["state"] == "completed"
        outcome = client.get(f"/api/research/{run_id}/outcome").json()["outcome"]
        assert outcome["status"] == "bankruptcy"

        timeline = client.get(f"/api/research/{run_id}/timeline").json()["events"]
        evidence_key = timeline[-1]["evidence_ids"][0]
        evidence = client.get(f"/api/research/evidence/{evidence_key}", params={"run_id": run_id})
        assert evidence.status_code == 200
        assert evidence.json()["evidence_key"] == evidence_key

        patterns = client.get(f"/api/research/{run_id}/patterns")
        assert patterns.status_code == 200
        assert patterns.json()["status"] == "available"
        pattern_payload = patterns.json()
        assert len(pattern_payload["similar_cases"]) == 2
        assert pattern_payload["archetype"] == "Fixed-cost liquidity crunch"
        assert all(
            item["similarities"] and item["differences"]
            for item in pattern_payload["similar_cases"]
        )

        reply = client.post(
            f"/api/research/{run_id}/assistant/messages",
            json={"text": "When was the Chapter 11 filing?", "language": "en"},
        )
        assert reply.status_code == 200
        assert "[E-001]" in reply.text


def test_bundled_demo_card_can_start_a_run_by_cik_when_its_short_id_is_not_a_database_id() -> None:
    with TestClient(app) as client:
        created = client.post("/api/research", json={"company_id": "bird", "cik": "1577967", "use_replay": True})
        assert created.status_code == 202
        assert created.json()["company"]["legal_name"] == "Bird Global, Inc."
        assert client.get(f"/api/research/{created.json()['id']}").json()["state"] == "completed"
