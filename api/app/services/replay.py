"""Load a safe, structured saved case into a new run for offline demos."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from ..models import (
    Claim,
    Company,
    Event,
    Evidence,
    Hypothesis,
    Inflection,
    Metric,
    OutcomeAssessment,
    ResearchRun,
    Source,
)
from .research import GRAPH_STAGES


def _read_case(fixtures_dir: Path, cik: str | None) -> dict[str, Any] | None:
    path = fixtures_dir / "demo_cases.json"
    if not path.exists() or not cik:
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    cases = raw.get("companies")
    if isinstance(cases, dict):
        return cases.get(str(cik))
    for case in raw.get("cases", []):
        if str(case.get("company", {}).get("cik")) == str(cik):
            return case
    return None


def _date(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _replay_pattern_match(
    raw_match: dict[str, Any] | None, fixtures_dir: Path, company_name: str | None
) -> dict[str, Any] | None:
    """Turn a compact fixture pattern reference into the public pattern contract.

    Demo fixtures intentionally store only stable case keys.  The report/API needs
    the matching archetype and two readable comparison notes, without pretending
    those notes are evidence from the active company.
    """
    if not isinstance(raw_match, dict):
        return None
    archetype_key = str(raw_match.get("archetype_key", ""))
    if not archetype_key:
        return None
    try:
        knowledge_root = fixtures_dir.parent / "knowledge"
        archetypes = json.loads((knowledge_root / "archetypes.json").read_text(encoding="utf-8"))
        cases = json.loads((knowledge_root / "cases.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {**raw_match, "similar_cases": []}

    archetype = next(
        (item for item in archetypes.get("archetypes", []) if item.get("key") == archetype_key),
        {},
    )
    cases_by_key = {str(item.get("key")): item for item in cases.get("cases", [])}
    active_name = (company_name or "").casefold()
    selected: list[dict[str, Any]] = []
    for key in raw_match.get("similar_case_keys", []):
        item = cases_by_key.get(str(key))
        if item and str(item.get("company", "")).casefold() != active_name:
            selected.append(item)
    if len(selected) < 2:
        for item in cases.get("cases", []):
            if (
                archetype_key in item.get("archetype_keys", [])
                and str(item.get("company", "")).casefold() != active_name
                and item not in selected
            ):
                selected.append(item)
            if len(selected) == 2:
                break

    similarities = [str(item) for item in raw_match.get("similarities", [])]
    differences = [str(item) for item in raw_match.get("differences", [])]
    comparable_cases = [
        {
            "key": item.get("key"),
            "name": item.get("company"),
            "outcome": item.get("outcome"),
            "summary": item.get("summary"),
            "similarities": similarities or [str(signal) for signal in item.get("signals", [])],
            "differences": differences
            or [str(difference) for difference in item.get("differences_to_check", [])],
            "similarity": "; ".join(similarities or item.get("signals", [])),
            "difference": "; ".join(differences or item.get("differences_to_check", [])),
        }
        for item in selected[:2]
    ]
    return {
        "archetype_key": archetype_key,
        "archetype": archetype.get("name", archetype_key.replace("_", " ").title()),
        "score": raw_match.get("score", 1.0),
        "description": archetype.get("definition", raw_match.get("description", "")),
        "similarities": similarities,
        "differences": differences or [str(archetype.get("caution", ""))],
        "similar_cases": comparable_cases,
    }


def load_replay_case(db: Session, run: ResearchRun, company: Company, fixtures_dir: Path) -> bool:
    """Populate a new run from JSON fixtures. Fixtures contain no user audio or secrets."""
    case = _read_case(fixtures_dir, company.cik)
    if not case:
        return False
    source_by_token: dict[str, Source] = {}
    for index, item in enumerate(case.get("sources", [])):
        source = Source(
            run_id=run.id,
            url=item["url"],
            publisher=item.get("publisher"),
            published_at=_date(item.get("published_at")),
            source_type=item.get("source_type", item.get("type", "filing")),
            title=item.get("title"),
            content_hash=item.get("content_hash") or hashlib.sha256(
                f"{run.id}:{item['url']}".encode()
            ).hexdigest(),
        )
        db.add(source)
        db.flush()
        source_by_token[str(item.get("source_key", item.get("id", index)))] = source
        source_by_token[item["url"]] = source

    for index, item in enumerate(case.get("evidence", [])):
        source = source_by_token.get(
            str(item.get("source_key", item.get("source_id", item.get("source_index", 0))))
        )
        if source is None and source_by_token:
            source = next(iter(source_by_token.values()))
        if source is None:
            source = Source(
                run_id=run.id,
                url=item.get("url", "https://example.invalid/fixture"),
                source_type="fixture",
                content_hash=hashlib.sha256(f"fixture-source-{index}-{run.id}".encode()).hexdigest(),
            )
            db.add(source)
            db.flush()
        db.add(
            Evidence(
                run_id=run.id,
                source_id=source.id,
                evidence_key=item.get("evidence_key", item.get("key", f"E-{index + 1:03d}")),
                text=item["text"],
                quote_start=item.get("quote_start"),
                quote_end=item.get("quote_end"),
                content_hash=item.get("content_hash") or hashlib.sha256(item["text"].encode("utf-8")).hexdigest(),
            )
        )

    for item in case.get("events", []):
        db.add(
            Event(
                run_id=run.id,
                date=item["date"],
                date_precision=item.get("date_precision", "day"),
                category=item.get("category", "business"),
                description=item["description"],
                evidence_ids=item.get("evidence_ids", item.get("evidence_keys", [])),
                confidence=item.get("confidence", "moderate"),
                verified=item.get("verified", True),
            )
        )
    for item in case.get("metrics", []):
        db.add(
            Metric(
                run_id=run.id,
                metric=item["metric"],
                period=item["period"],
                value=item["value"],
                unit=item.get("unit", "USD"),
                kind=item.get("kind", "disclosed"),
                evidence_id=item.get("evidence_id", item.get("evidence_key")),
            )
        )
    outcome = case.get("outcome")
    if outcome:
        db.add(
            OutcomeAssessment(
                run_id=run.id,
                status=outcome.get("status", "unknown"),
                summary=outcome.get("summary", "No outcome assessment was recorded."),
                evidence_ids=outcome.get("evidence_ids", outcome.get("evidence_keys", [])),
                confidence=outcome.get("confidence", "moderate"),
                verified=outcome.get("verified", True),
            )
        )
    for item in case.get("hypotheses", []):
        db.add(
            Hypothesis(
                run_id=run.id,
                mechanism=item["mechanism"],
                supports=item.get("supports", []),
                contradicts=item.get("contradicts", []),
                missing=item.get("missing", []),
                confidence=item.get("confidence", "insufficient"),
                critic_notes=item.get("critic_notes"),
            )
        )
    for item in case.get("inflections", []):
        db.add(
            Inflection(
                run_id=run.id,
                period=item["period"],
                metric=item["metric"],
                size=item["size"],
                explanation=item["explanation"],
                evidence_ids=item.get("evidence_ids", item.get("evidence_keys", [])),
            )
        )
    for item in case.get("claims", []):
        db.add(
            Claim(
                run_id=run.id,
                text=item["text"],
                cited_evidence=item.get("cited_evidence", item.get("cited_evidence_keys", [])),
                result=item.get("result", "supported"),
                reason=item.get("reason"),
            )
        )
    run.node_status = {stage: "done" for stage in GRAPH_STAGES}
    run.state = case.get("state", "completed")
    run.final_report = case.get("report") or {
        "company": case.get("company", {}),
        "outcome": outcome,
        "timeline": case.get("events", []),
        "financials": case.get("metrics", []),
        "inflections": case.get("inflections", []),
        "hypotheses": case.get("hypotheses", []),
        "claims": [item for item in case.get("claims", []) if item.get("result") == "supported"],
        "pattern_match": _replay_pattern_match(
            case.get("pattern_match"), fixtures_dir, company.legal_name
        ),
        "verification": {
            "checked": len(case.get("claims", [])),
            "supported": len([item for item in case.get("claims", []) if item.get("result") == "supported"]),
            "removed": len([item for item in case.get("claims", []) if item.get("result") != "supported"]),
        },
        "limitations": "Synthetic replay fixture. It demonstrates evidence flow, not investment research.",
    }
    db.add(run)
    db.commit()
    return True
