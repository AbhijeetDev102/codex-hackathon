"""Live-run executor that joins provider adapters, deterministic analysis, and storage.

Replay runs deliberately bypass this module and load bounded fixture data. Live runs
use the same graph but can finish as ``completed_with_limits`` when an optional
provider is unavailable; they never silently convert missing evidence into facts.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete

from ..config import get_settings
from ..db import SessionLocal
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
from ..providers.base import ProviderUnavailable
from ..providers.cache import RequestCache
from ..providers.cerebras import CerebrasProvider
from ..providers.exa import ExaProvider
from ..providers.openai import OpenAIProvider
from ..providers.sec import SecProvider
from ..services.research import GRAPH_STAGES
from . import nodes
from .state import RunState
from .workflow import NodeHandler, build_research_graph


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _citation_keys(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return list(dict.fromkeys(str(item) for item in value if item))


def _source_url(cik: str, accession: str | None, primary_document: str | None) -> str:
    if accession and primary_document:
        accession_number = accession.replace("-", "")
        return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_number}/{primary_document}"
    return f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={int(cik):010d}"


def _xbrl_points(company_facts: dict[str, Any], cik: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Extract a small auditable financial series from standard US-GAAP tags."""

    tags = {
        "revenue": ("Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax"),
        "cash": ("CashAndCashEquivalentsAtCarryingValue",),
        "net_loss": ("NetIncomeLoss",),
        "operating_cash_flow": ("NetCashProvidedByUsedInOperatingActivities",),
    }
    facts = company_facts.get("facts", {}).get("us-gaap", {})
    sources: list[dict[str, Any]] = []
    metrics: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    sequence = 1
    seen: set[tuple[str, str]] = set()
    for metric, possible_tags in tags.items():
        units: list[dict[str, Any]] = []
        tag_name = None
        for candidate in possible_tags:
            entry = facts.get(candidate, {})
            candidate_units = entry.get("units", {}).get("USD", [])
            if candidate_units:
                units, tag_name = candidate_units, candidate
                break
        for point in sorted(units, key=lambda item: (item.get("end", ""), item.get("filed", ""))):
            if point.get("form") not in {"10-Q", "10-K"} or not point.get("end"):
                continue
            fiscal_period = point.get("fp") or "FY"
            period = f"{point.get('fy', point['end'][:4])}-{fiscal_period}"
            key = (metric, period)
            if key in seen or not isinstance(point.get("val"), (int, float)):
                continue
            seen.add(key)
            evidence_key = f"E-{sequence:03d}"
            source_key = f"S-XBRL-{sequence:03d}"
            sequence += 1
            raw_value = float(point["val"])
            url = _source_url(cik, point.get("accn"), point.get("primaryDocument"))
            text = f"SEC Company Facts reports {tag_name} of {raw_value:,.0f} USD for the period ending {point['end']} (form {point.get('form')})."
            sources.append({"source_key": source_key, "url": url, "publisher": "U.S. Securities and Exchange Commission", "source_type": "filing", "title": f"SEC XBRL {tag_name}"})
            evidence.append({"evidence_key": evidence_key, "source_key": source_key, "text": text, "quote_start": 0, "quote_end": len(text)})
            metrics.append({"metric": metric, "period": period, "value": raw_value, "unit": "USD", "kind": "disclosed", "evidence_key": evidence_key})
    by_metric: dict[str, list[dict[str, Any]]] = {}
    for metric in metrics:
        by_metric.setdefault(metric["metric"], []).append(metric)
    kept = [metric for values in by_metric.values() for metric in values[-12:]]
    keys = {metric["evidence_key"] for metric in kept}
    return sources, kept, [item for item in evidence if item["evidence_key"] in keys]


async def _collect_live(state: RunState, sec: SecProvider, exa: ExaProvider) -> dict[str, Any]:
    """Collect independent public-data sources without discarding SEC evidence.

    Each upstream request is useful on its own.  In particular, a temporary DNS
    failure for a news search must not turn a successful SEC Company Facts
    response into a failed research collection.  We record a plain-language
    limitation for the run and let downstream nodes work only with the evidence
    that was actually retrieved.
    """

    company = state.get("company", {})
    cik = str(company.get("cik", ""))
    if not cik:
        raise ValueError("A confirmed company CIK is required for live collection.")
    submissions_result, facts_result = await asyncio.gather(
        sec.submissions(cik), sec.company_facts(cik), return_exceptions=True
    )
    errors: list[str] = []
    submissions: dict[str, Any] = {}
    facts: dict[str, Any] = {}
    if isinstance(submissions_result, Exception):
        errors.append("SEC filing-index data was temporarily unavailable; filing timeline coverage is limited.")
    else:
        submissions = submissions_result
    if isinstance(facts_result, Exception):
        errors.append("SEC XBRL financial data was temporarily unavailable; financial analysis is limited.")
    else:
        facts = facts_result
    sources, metrics, evidence = _xbrl_points(facts, cik)
    filings = submissions.get("filings", {}).get("recent", {})
    events: list[dict[str, Any]] = []
    forms, dates = filings.get("form", []), filings.get("filingDate", [])
    accessions, documents = filings.get("accessionNumber", []), filings.get("primaryDocument", [])
    for index, form in enumerate(forms[:80]):
        if form != "8-K" or index >= len(dates) or not dates[index]:
            continue
        evidence_key, source_key = f"E-FILING-{index:03d}", f"S-FILING-{index:03d}"
        url = _source_url(cik, accessions[index] if index < len(accessions) else None, documents[index] if index < len(documents) else None)
        text = f"SEC submissions index records an 8-K filed by {company.get('legal_name', 'the company')} on {dates[index]}."
        sources.append({"source_key": source_key, "url": url, "publisher": "U.S. Securities and Exchange Commission", "source_type": "filing", "title": "SEC 8-K filing"})
        evidence.append({"evidence_key": evidence_key, "source_key": source_key, "text": text, "quote_start": 0, "quote_end": len(text)})
        events.append({"date": dates[index], "date_precision": "day", "category": "sec_filing", "description": "An 8-K filing was recorded; detailed extraction may add a more specific event.", "evidence_ids": [evidence_key], "confidence": "moderate", "verified": True, "form": "8-K"})
    try:
        results = await exa.search(f"{company.get('legal_name')} financial distress filing", limit=10)
        for index, result in enumerate(results):
            content, url = str(result.get("text") or result.get("highlights") or "").strip(), str(result.get("url") or "")
            if not content or not url:
                continue
            source_key, evidence_key = f"S-NEWS-{index:03d}", f"E-NEWS-{index:03d}"
            sources.append({"source_key": source_key, "url": url, "publisher": result.get("author") or "Public reporting", "source_type": "news", "title": result.get("title")})
            evidence.append({"evidence_key": evidence_key, "source_key": source_key, "text": content[:4000], "quote_start": 0, "quote_end": min(500, len(content))})
    except Exception:
        # Discovery is supplementary.  Do not expose transport details or drop
        # the primary SEC evidence when it is down.
        errors.append("Supplementary public-reporting discovery was unavailable; SEC evidence was retained.")
    result: dict[str, Any] = {"sources": sources, "evidence": evidence, "events": events, "metrics": metrics}
    if errors:
        result["errors"] = errors
    return result


async def _extract_live(state: RunState, cerebras: CerebrasProvider) -> dict[str, Any]:
    chunks = [str(item.get("text", "")) for item in state.get("evidence", []) if item.get("text")]
    if not chunks:
        return {}
    try:
        extracted = await cerebras.extract_events(chunks[:30])
    except ProviderUnavailable:
        return {}
    known_evidence = {str(item.get("evidence_key")) for item in state.get("evidence", [])}
    events = list(state.get("events", []))
    for item in extracted:
        citations = _citation_keys(item.get("evidence_ids"))
        if not item.get("date") or not item.get("description") or not citations or not set(citations).issubset(known_evidence):
            continue
        events.append({"date": str(item["date"]), "date_precision": str(item.get("date_precision", "day")), "category": str(item.get("category", "business_event")), "description": str(item["description"]), "evidence_ids": citations, "confidence": str(item.get("confidence", "moderate")), "verified": True})
    return {"events": events}


async def _propose_live(state: RunState, reasoning: OpenAIProvider) -> dict[str, Any]:
    """Ask for structured competing hypotheses only when reasoning is configured."""

    if not reasoning.settings.openai_api_key:
        return {}
    evidence = state.get("evidence", [])[:20]
    context = "\n".join(f"[{item.get('evidence_key')}] {item.get('text', '')[:500]}" for item in evidence)
    prompt = "Using only the evidence below, return JSON with hypotheses and claims. Produce at most three competing hypotheses. Every claim requires evidence_ids. Never claim proven causation.\n\n" + context
    try:
        response = await reasoning.complete([{"role": "system", "content": "Return valid JSON only."}, {"role": "user", "content": prompt}], response_format={"type": "json_object"})
        payload = json.loads(response.content)
    except (ValueError, KeyError):
        return {}
    valid = {str(item.get("evidence_key")) for item in evidence}
    hypotheses: list[dict[str, Any]] = []
    for item in payload.get("hypotheses", [])[:3]:
        supports = _citation_keys(item.get("supports") or item.get("evidence_ids"))
        if not supports or not set(supports).issubset(valid):
            continue
        hypotheses.append({"mechanism": str(item.get("mechanism", "")), "supports": supports, "contradicts": _citation_keys(item.get("contradicts")), "missing": [str(value) for value in item.get("missing", [])][:5], "confidence": str(item.get("confidence", "insufficient")).lower(), "critic_notes": None})
    claims = [{"text": str(item.get("text", "")), "cited_evidence": _citation_keys(item.get("evidence_ids"))} for item in payload.get("claims", [])[:12] if item.get("text")]
    return {"hypotheses": hypotheses, "claims": claims}


async def _match_patterns(state: RunState) -> dict[str, Any]:
    """Match only local, hand-written knowledge; never invent a comparable case.

    This deterministic prototype intentionally avoids claiming semantic embeddings or
    pgvector retrieval. A match needs at least one explicit active-run signal, then
    returns two tagged historical notes with their known differences to check.
    """
    knowledge_root = get_settings().fixture_path.parent / "knowledge"
    archetype_path = knowledge_root / "archetypes.json"
    case_path = knowledge_root / "cases.json"
    if not archetype_path.exists() or not case_path.exists():
        return {"pattern_match": None, "patterns": []}
    try:
        patterns = json.loads(archetype_path.read_text(encoding="utf-8")).get("archetypes", [])
        cases = json.loads(case_path.read_text(encoding="utf-8")).get("cases", [])
    except (OSError, ValueError):
        return {"pattern_match": None, "patterns": []}

    text_parts = [
        str(item.get("mechanism", "")) for item in state.get("hypotheses", [])
    ] + [
        f"{item.get('category', '')} {item.get('description', '')}" for item in state.get("events", [])
    ]
    text = " ".join(text_parts).casefold()
    best: dict[str, Any] | None = None
    matched_signals: list[str] = []
    for pattern in patterns:
        matched = [
            str(signal)
            for signal in pattern.get("signals", [])
            if str(signal).casefold() in text
        ]
        if len(matched) > len(matched_signals):
            best, matched_signals = pattern, matched
    if not best or not matched_signals:
        return {"pattern_match": None, "patterns": []}

    active_company = str(state.get("company", {}).get("legal_name", "")).casefold()
    archetype_key = str(best.get("key", ""))
    candidates: list[dict[str, Any]] = []
    for case in cases:
        if archetype_key not in {str(key) for key in case.get("archetype_keys", [])}:
            continue
        case_name = str(case.get("company", ""))
        # Do not compare a company to its own historical note.
        if active_company and case_name and (
            case_name.casefold() in active_company or active_company in case_name.casefold()
        ):
            continue
        shared_signals = [
            str(signal)
            for signal in case.get("signals", [])
            if str(signal).casefold() in text
        ]
        similarities = shared_signals or [f"Shares the {best.get('name', 'selected')} archetype"]
        differences = [str(item) for item in case.get("differences_to_check", [])]
        candidates.append(
            {
                "key": str(case.get("key", "")),
                "name": case_name or "Comparable case",
                "outcome": str(case.get("outcome", "unknown")),
                "summary": str(case.get("summary", "")),
                "similarities": similarities,
                "differences": differences,
                # Singular strings keep the existing frontend API mapper compatible.
                "similarity": "; ".join(similarities),
                "difference": "; ".join(differences) or "Review the source case for differences.",
                "_rank": len(shared_signals),
            }
        )
    comparable_cases = sorted(candidates, key=lambda item: (-int(item["_rank"]), item["name"]))[:2]
    for case in comparable_cases:
        case.pop("_rank", None)
    score = len(matched_signals) / max(1, len(best.get("signals", [])))
    match = {
        "archetype_key": archetype_key,
        "archetype": str(best.get("name", "No good match")),
        "score": round(score, 2),
        "description": str(best.get("definition", "")),
        "similarities": matched_signals,
        "differences": [str(best.get("caution", ""))] if best.get("caution") else [],
        "similar_cases": comparable_cases,
    }
    return {"pattern_match": match, "patterns": [match]}


def _set_stage(run_id: str, node: str, status: str) -> None:
    db = SessionLocal()
    try:
        run = db.get(ResearchRun, run_id)
        if run:
            statuses = dict(run.node_status or {})
            statuses[node] = status
            run.node_status = statuses
            db.add(run)
            db.commit()
    finally:
        db.close()


def _staged(run_id: str, name: str, handler: NodeHandler) -> NodeHandler:
    async def wrapped(state: RunState) -> dict[str, Any]:
        _set_stage(run_id, name, "running")
        try:
            result = handler(state)
            if hasattr(result, "__await__"):
                result = await result  # type: ignore[assignment,misc]
            _set_stage(run_id, name, "done")
            return result  # type: ignore[return-value]
        except Exception:
            _set_stage(run_id, name, "failed")
            raise
    return wrapped


def _replace_results(db: Any, run_id: str, state: RunState) -> None:
    """Persist graph output in dependency order using E-keys as stable receipts."""

    for model in (Claim, Hypothesis, Inflection, OutcomeAssessment, Metric, Event, Evidence, Source):
        db.execute(delete(model).where(model.run_id == run_id))
    source_by_key: dict[str, Source] = {}
    for index, item in enumerate(state.get("sources", [])):
        source = Source(run_id=run_id, url=str(item.get("url") or f"https://example.invalid/source/{index}"), publisher=item.get("publisher"), source_type=str(item.get("source_type", "filing")), title=item.get("title"), content_hash=hashlib.sha256(f"{item.get('url', '')}:{item.get('title', '')}:{index}".encode()).hexdigest())
        db.add(source)
        db.flush()
        source_by_key[str(item.get("source_key", index))] = source
    for index, item in enumerate(state.get("evidence", [])):
        source = source_by_key.get(str(item.get("source_key")))
        if source is None:
            source = Source(run_id=run_id, url="https://example.invalid/unmapped-evidence", source_type="generated_index", content_hash=hashlib.sha256(f"unmapped-{index}".encode()).hexdigest())
            db.add(source)
            db.flush()
        db.add(Evidence(run_id=run_id, source_id=source.id, evidence_key=str(item.get("evidence_key", f"E-{index + 1:03d}")), text=str(item.get("text", "")), quote_start=item.get("quote_start"), quote_end=item.get("quote_end"), content_hash=hashlib.sha256(str(item.get("text", "")).encode()).hexdigest()))
    for item in state.get("events", []):
        db.add(Event(run_id=run_id, date=str(item.get("date", "")), date_precision=str(item.get("date_precision", "day")), category=str(item.get("category", "business_event")), description=str(item.get("description", "")), evidence_ids=_citation_keys(item.get("evidence_ids")), confidence=str(item.get("confidence", "moderate")), verified=bool(item.get("verified", False))))
    for item in state.get("metrics", []):
        db.add(Metric(run_id=run_id, metric=str(item.get("metric")), period=str(item.get("period")), value=float(item.get("value", 0)), unit=str(item.get("unit", "USD")), kind=str(item.get("kind", "disclosed")), evidence_id=item.get("evidence_id") or item.get("evidence_key")))
    outcome = state.get("outcome")
    if outcome:
        db.add(OutcomeAssessment(run_id=run_id, status=str(outcome.get("status", "unknown")), summary=str(outcome.get("summary", "No outcome assessment was recorded.")), evidence_ids=_citation_keys(outcome.get("evidence_ids")), confidence=str(outcome.get("confidence", "insufficient")), verified=bool(outcome.get("verified", False))))
    for item in state.get("inflections", []):
        db.add(Inflection(run_id=run_id, period=str(item.get("period")), metric=str(item.get("metric")), size=float(item.get("size", 0)), explanation=str(item.get("explanation", "")), evidence_ids=_citation_keys(item.get("evidence_ids"))))
    for item in state.get("hypotheses", []):
        db.add(Hypothesis(run_id=run_id, mechanism=str(item.get("mechanism", "")), supports=_citation_keys(item.get("supports")), contradicts=_citation_keys(item.get("contradicts")), missing=[str(value) for value in item.get("missing", [])], confidence=str(item.get("confidence", "insufficient")), critic_notes=item.get("critic_notes")))
    for item in [*state.get("claims", []), *state.get("rejected_claims", [])]:
        db.add(Claim(run_id=run_id, text=str(item.get("text", "")), cited_evidence=_citation_keys(item.get("cited_evidence")), result=str(item.get("result", "unsupported")), reason=item.get("reason")))


async def run_research(run_id: str) -> None:
    """Execute a non-replay run and persist its bounded, citation-safe result."""

    settings = get_settings()
    if settings.is_replay:
        return
    db = SessionLocal()
    try:
        run = db.get(ResearchRun, run_id)
        if not run:
            return
        company = db.get(Company, run.company_id)
        if not company:
            run.state, run.error_code = "completed_with_limits", "company_missing"
            db.commit()
            return
        run.state = "running"
        db.add(run)
        db.commit()
        cache = RequestCache(settings.fixture_path, settings.demo_mode)
        sec, exa = SecProvider(settings, cache), ExaProvider(settings, cache)
        cerebras, reasoning = CerebrasProvider(settings, cache), OpenAIProvider(settings, cache)
        overrides: dict[str, NodeHandler] = {
            "resolve_company": lambda _: {"company": {"id": company.id, "legal_name": company.legal_name, "cik": company.cik, "ticker": company.ticker}},
            "collect": lambda state: _collect_live(state, sec, exa),
            "extract_events": lambda state: _extract_live(state, cerebras),
            "compute_financials": nodes.compute_financials,
            "assess_outcome": nodes.assess_outcome_node,
            "detect_inflections": nodes.detect_inflections_node,
            "propose_hypotheses": lambda state: _propose_live(state, reasoning),
            "critic": nodes.passthrough,
            "verify_claims": nodes.verify_claims_node,
            "match_patterns": _match_patterns,
            "write_report": nodes.write_report_node,
        }
        graph = build_research_graph({name: _staged(run_id, name, handler) for name, handler in overrides.items()})
        result = await graph.ainvoke({"run_id": run_id, "company": {"id": company.id, "legal_name": company.legal_name, "cik": company.cik, "ticker": company.ticker}, "sources": [], "evidence": [], "events": [], "metrics": [], "claims": [], "hypotheses": [], "revise_round": 0, "node_status": {stage: "pending" for stage in GRAPH_STAGES}})
        _replace_results(db, run_id, result)
        run = db.get(ResearchRun, run_id)
        assert run is not None
        run.final_report = result.get("report")
        run.state = "completed_with_limits" if result.get("errors") else "completed"
        if result.get("errors"):
            run.error_code, run.error_message = "partial_provider_failure", "; ".join(result["errors"])
        run.completed_at = _utc_now()
        db.add(run)
        db.commit()
    except Exception as error:
        db.rollback()
        run = db.get(ResearchRun, run_id)
        if run:
            run.state, run.error_code, run.error_message, run.completed_at = "completed_with_limits", "run_failed", str(error)[:1000], _utc_now()
            db.add(run)
            db.commit()
    finally:
        db.close()
